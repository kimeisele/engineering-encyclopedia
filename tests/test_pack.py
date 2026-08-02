"""Context pack tests (Section 6): hard limits for every corpus query at
every detail level, deterministic hashing, and caps."""

import unittest
from pathlib import Path

import yaml

from encyclopedia.canonical import canonical_bytes
from encyclopedia.loader import load_nodes
from encyclopedia.pack import (
    DETAIL_LEVELS,
    MAX_EXCLUDED,
    MAX_PRIMARY,
    MAX_RELEVANCE_WORDS,
    MAX_SUPPORTING,
    WORD_BUDGETS,
    PackOptions,
    compose_pack,
)
from encyclopedia.retrieval import RetrievalIndex, fts5_available
from encyclopedia.words import count_words

ROOT = Path(__file__).resolve().parents[1]
QUERIES = yaml.safe_load(open(ROOT / "evaluations" / "queries.yaml", encoding="utf-8"))


class TestPackLimits(unittest.TestCase):
    def test_limits_hold_for_every_corpus_query(self):
        nodes = load_nodes()
        backends = ["token-overlap"] + (["fts5"] if fts5_available() else [])
        for backend in backends:
            index = RetrievalIndex(nodes, backend=backend)
            for query in QUERIES:
                for detail in DETAIL_LEVELS:
                    with self.subTest(backend=backend, detail=detail, query=query["query"]):
                        pack = compose_pack(
                            nodes, index, query["query"], PackOptions(detail=detail)
                        )
                        primary = pack["context_pack"]["primary"]
                        supporting = pack["context_pack"]["supporting"]
                        self.assertLessEqual(len(primary), MAX_PRIMARY)
                        self.assertLessEqual(len(supporting), MAX_SUPPORTING)
                        self.assertLessEqual(len(pack["trace"]["excluded"]), MAX_EXCLUDED)
                        self.assertLessEqual(
                            count_words(pack), WORD_BUDGETS[detail],
                            f"{detail} pack over budget",
                        )
                        for entry in primary + supporting:
                            for key in ("id", "version", "hash"):
                                self.assertIn(key, entry, f"{detail} entry lacks {key}")
                            self.assertLessEqual(
                                count_words(entry["relevance"]), MAX_RELEVANCE_WORDS
                            )

    def test_never_truncates_primary_below_required(self):
        # The top-ranked required node must survive truncation at every
        # detail level (lowest-ranked nodes are dropped first).
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        for query in QUERIES:
            for detail in DETAIL_LEVELS:
                pack = compose_pack(
                    nodes, index, query["query"], PackOptions(detail=detail)
                )
                selected = pack["trace"]["selected"]
                self.assertIn(query["required"][0], selected, query["query"])

    def test_hash_is_deterministic(self):
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        first = compose_pack(nodes, index, QUERIES[0]["query"], PackOptions())
        second = compose_pack(nodes, index, QUERIES[0]["query"], PackOptions())
        self.assertEqual(first["context_pack_hash"], second["context_pack_hash"])
        self.assertEqual(len(first["context_pack_hash"]), 12)

    def test_hash_binds_content(self):
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        base = compose_pack(nodes, index, QUERIES[0]["query"], PackOptions())
        tweaked = compose_pack(nodes, index, QUERIES[0]["query"], PackOptions())
        tweaked["context_pack"]["primary"][0]["relevance"] = "changed relevance line"
        recomputed = _hash_without_own_field(tweaked)
        self.assertNotEqual(base["context_pack_hash"], recomputed)

    def test_max_primary_capped_at_three(self):
        options = PackOptions(max_primary=99, max_supporting=99)
        self.assertEqual(options.max_primary, 3)
        self.assertEqual(options.max_supporting, 3)

    def test_detail_levels_are_strictly_growing(self):
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        query = QUERIES[0]["query"]
        compact = compose_pack(nodes, index, query, PackOptions(detail="compact"))
        guidance = compose_pack(nodes, index, query, PackOptions(detail="guidance"))
        full = compose_pack(nodes, index, query, PackOptions(detail="full"))
        self.assertLess(count_words(compact), count_words(guidance))
        self.assertLess(count_words(guidance), count_words(full))

    def test_long_request_is_clamped_to_budget(self):
        # Review finding F2: a request longer than the budget must not leave
        # an over-budget pack; request.original is clamped deterministically.
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        long_request = " ".join(["request"] * 300)
        pack = compose_pack(nodes, index, long_request, PackOptions(detail="compact"))
        self.assertLessEqual(count_words(pack), WORD_BUDGETS["compact"])
        self.assertTrue(pack["trace"]["truncated"])
        self.assertLessEqual(count_words(pack["request"]["original"]), 120)

    def test_frozen_experiment_packs_match_corpus(self):
        # The frozen treatment packs are evidence of the corpus the Section 8
        # experiment ran against: the original eight nodes. The corpus has
        # since grown to ten (docs/CORPUS_RULE.md, DEVIATIONS D10), so this
        # test recomposes against the pinned experiment corpus — an edit to
        # any of those eight nodes still fails loudly instead of silently
        # breaking verify-report of the recorded runs.
        experiment_ids = {
            "reliability.idempotency",
            "reliability.retry-semantics",
            "concurrency.race-conditions",
            "python.files.atomic-replacement",
            "python.processes.subprocess-safety",
            "security.input-validation",
            "testing.coverage-limitations",
            "observability.error-context",
        }
        all_nodes = load_nodes()
        corpus_ids = {n.id for n in all_nodes}
        self.assertTrue(experiment_ids <= corpus_ids, "experiment corpus ids missing")
        nodes = [n for n in all_nodes if n.id in experiment_ids]
        requests = {
            "e1": "Write a worker that consumes jobs from a queue and charges a customer.",
            "e2": "Write a Python function that runs a git command with a user-supplied branch name.",
            "e3": "Write a function that updates a JSON config file on disk.",
        }
        for task, request in requests.items():
            with self.subTest(task=task):
                frozen_path = ROOT / "experiments" / "packs" / f"{task}.yaml"
                frozen = yaml.safe_load(frozen_path.read_text(encoding="utf-8"))
                backend = frozen["retrieval_backend"]
                if backend == "fts5" and not fts5_available():
                    self.skipTest("fts5 unavailable in this interpreter")
                index = RetrievalIndex(nodes, backend=backend)
                recomposed = compose_pack(
                    nodes, index, request, PackOptions(detail="guidance")
                )
                self.assertEqual(
                    recomposed["context_pack_hash"], frozen["context_pack_hash"], task
                )
                self.assertEqual(
                    recomposed["knowledge_revision"], frozen["knowledge_revision"], task
                )


class TestNoMatch(unittest.TestCase):
    """Slice 1: retrieval must not invent relevance.

    A zero-score node must never be selected as primary; a query with no
    overlap at all yields an empty pack marked ``no_match`` with a trace
    reason. Both backends behave identically in this case.
    """

    UNKNOWN = "zyxwvutsrqponmlkjihgfedcba quux plugh frobnicate"
    VAGUE = "the and of it to"
    NEAR_MISS = "a worker queue that charges the same customer job twice"

    def _indexes(self, nodes):
        backends = ["token-overlap"] + (["fts5"] if fts5_available() else [])
        return [RetrievalIndex(nodes, backend=b) for b in backends]

    def test_completely_unknown_query_emits_no_match_pack(self):
        nodes = load_nodes()
        for index in self._indexes(nodes):
            with self.subTest(backend=index.backend):
                pack = compose_pack(nodes, index, self.UNKNOWN, PackOptions())
                self.assertTrue(pack["trace"]["no_match"])
                self.assertEqual(pack["context_pack"]["primary"], [])
                self.assertEqual(pack["context_pack"]["supporting"], [])
                self.assertEqual(pack["trace"]["selected"], [])
                self.assertTrue(pack["trace"]["reason"])
                self.assertEqual(len(pack["context_pack_hash"]), 12)

    def test_zero_score_nodes_never_primary(self):
        # The invariant behind the no-match rule: whatever the query, every
        # primary node carries a positive score; ties no longer promote
        # alphabetically-early zero-score nodes to primary.
        nodes = load_nodes()
        for index in self._indexes(nodes):
            for query in (self.UNKNOWN, self.VAGUE, self.NEAR_MISS):
                with self.subTest(backend=index.backend, query=query[:24]):
                    ranked = dict(index.search(query))
                    pack = compose_pack(nodes, index, query, PackOptions())
                    for entry in pack["context_pack"]["primary"]:
                        self.assertGreater(ranked[entry["id"]], 0.0, entry["id"])

    def test_vague_query_still_selects(self):
        # A query of function words matches everything at a small positive
        # score; the pack is not empty and selection is deterministic.
        # no_match is reserved for zero overlap, not for low signal.
        nodes = load_nodes()
        for index in self._indexes(nodes):
            with self.subTest(backend=index.backend):
                pack = compose_pack(nodes, index, self.VAGUE, PackOptions())
                self.assertFalse(pack["trace"].get("no_match", False))
                self.assertTrue(pack["context_pack"]["primary"])

    def test_near_miss_query_selects_the_near_node(self):
        nodes = load_nodes()
        for index in self._indexes(nodes):
            with self.subTest(backend=index.backend):
                pack = compose_pack(nodes, index, self.NEAR_MISS, PackOptions())
                self.assertFalse(pack["trace"].get("no_match", False))
                primary_ids = {e["id"] for e in pack["context_pack"]["primary"]}
                self.assertIn("reliability.idempotency", primary_ids)


def _hash_without_own_field(pack):
    import hashlib

    from encyclopedia.canonical import canonical_bytes

    stripped = {k: v for k, v in pack.items() if k != "context_pack_hash"}
    return hashlib.sha256(canonical_bytes(stripped)).hexdigest()[:12]


if __name__ == "__main__":
    unittest.main()
