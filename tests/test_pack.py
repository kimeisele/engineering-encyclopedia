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


def _hash_without_own_field(pack):
    import hashlib

    from encyclopedia.canonical import canonical_bytes

    stripped = {k: v for k, v in pack.items() if k != "context_pack_hash"}
    return hashlib.sha256(canonical_bytes(stripped)).hexdigest()[:12]


if __name__ == "__main__":
    unittest.main()
