"""Retrieval tests (Section 5): per-backend determinism, backend equivalence,
performance, and corpus binding of packs."""

import time
import unittest
from pathlib import Path

import yaml

from encyclopedia.canonical import canonical_bytes
from encyclopedia.loader import load_nodes
from encyclopedia.pack import PackOptions, compose_pack
from encyclopedia.retrieval import RetrievalIndex, fts5_available

ROOT = Path(__file__).resolve().parents[1]
QUERIES = yaml.safe_load(open(ROOT / "evaluations" / "queries.yaml", encoding="utf-8"))


def available_backends():
    backends = ["token-overlap"]
    if fts5_available():
        backends.append("fts5")
    return backends


def pack_node_ids(pack):
    return [
        entry["id"]
        for section in ("primary", "supporting")
        for entry in pack["context_pack"][section]
    ]


class TestRetrievalBackends(unittest.TestCase):
    def test_both_backends_build(self):
        nodes = load_nodes()
        for backend in available_backends():
            with self.subTest(backend=backend):
                index = RetrievalIndex(nodes, backend=backend)
                self.assertEqual(index.backend, backend)
                results = index.search("worker processes the same job twice")
                self.assertTrue(results)
                for node_id, _score in results:
                    self.assertIn(node_id, {n.id for n in nodes})
                # FTS5 returns only lexically matching rows; token-overlap
                # returns all rows. Both are valid per Section 5.
                if backend == "fts5":
                    self.assertEqual(len(index.search("idempotency")), 1)
                else:
                    self.assertEqual(len(index.search("idempotency")), 8)

    def test_default_backend_is_reported(self):
        index = RetrievalIndex(load_nodes())
        self.assertIn(index.backend, ("fts5", "token-overlap"))

    def test_determinism_per_backend(self):
        # Byte-identical output on repeated identical queries within each
        # backend. Never asserted across backends.
        nodes = load_nodes()
        for backend in available_backends():
            with self.subTest(backend=backend):
                index = RetrievalIndex(nodes, backend=backend)
                for query in QUERIES:
                    first = index.search(query["query"])
                    second = index.search(query["query"])
                    self.assertEqual(first, second, query["query"])
                    pack_a = compose_pack(nodes, index, query["query"], PackOptions())
                    pack_b = compose_pack(nodes, index, query["query"], PackOptions())
                    self.assertEqual(
                        canonical_bytes(pack_a), canonical_bytes(pack_b), query["query"]
                    )

    def test_backend_equivalence(self):
        # Outcome, not ranking: every required node lands inside the
        # primary-plus-supporting pack, and no forbidden-to-dominate node
        # outranks all required nodes. Ranking equality is NOT asserted.
        nodes = load_nodes()
        for backend in available_backends():
            with self.subTest(backend=backend):
                index = RetrievalIndex(nodes, backend=backend)
                for query in QUERIES:
                    ranked = [nid for nid, _ in index.search(query["query"])]
                    pack = compose_pack(nodes, index, query["query"], PackOptions())
                    selected = set(pack_node_ids(pack))
                    for required in query["required"]:
                        self.assertIn(
                            required, selected,
                            f"{backend}: required {required} missing for {query['query']!r}",
                        )
                    min_required = min(ranked.index(r) for r in query["required"])
                    for forbidden in query["forbidden_to_dominate"]:
                        if forbidden in ranked:
                            self.assertGreater(
                                ranked.index(forbidden), min_required,
                                f"{backend}: {forbidden} dominates {query['query']!r}",
                            )

    def test_no_out_of_corpus_nodes_in_pack(self):
        nodes = load_nodes()
        corpus_ids = {n.id for n in nodes}
        for backend in available_backends():
            index = RetrievalIndex(nodes, backend=backend)
            for query in QUERIES:
                pack = compose_pack(nodes, index, query["query"], PackOptions())
                for node_id in pack_node_ids(pack):
                    self.assertIn(node_id, corpus_ids)

    def test_performance_under_200ms(self):
        # Index build plus all ten corpus queries on a cold start.
        nodes = load_nodes()
        start = time.perf_counter()
        index = RetrievalIndex(nodes)
        for query in QUERIES:
            index.search(query["query"])
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.2, f"index+queries took {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
