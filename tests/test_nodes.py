"""Corpus tests: exactly eight nodes, schema rules, hard limits, relations,
taxonomy bindings (Sections 3 and 4 of the founding brief)."""

import unittest
from pathlib import Path

from encyclopedia.loader import load_nodes, load_taxonomy
from encyclopedia.validate import (
    LIST_LIMITS,
    MAX_LIST_ENTRY_WORDS,
    MAX_NODE_WORDS,
    SUMMARY_MAX_WORDS,
    validate_all,
)
from encyclopedia.words import count_words

EXPECTED_IDS = {
    "reliability.idempotency",
    "reliability.retry-semantics",
    "concurrency.race-conditions",
    "python.files.atomic-replacement",
    "python.processes.subprocess-safety",
    "security.input-validation",
    "testing.coverage-limitations",
    "observability.error-context",
}

REQUIRED_FIELDS = {
    "id", "version", "title", "kind", "status", "summary", "intent_signals",
    "applies_when", "does_not_imply", "questions", "risks", "provenance",
    "keywords",
}

# every list-valued field whose entries must stay <= MAX_LIST_ENTRY_WORDS
LIST_FIELDS = (
    "intent_signals", "applies_when", "does_not_apply_when", "does_not_imply",
    "questions", "techniques", "risks", "tradeoffs",
)


class TestCorpus(unittest.TestCase):
    def test_exactly_eight_nodes(self):
        # The count is asserted: a short corpus fails rather than lowering
        # the expectation (Section 10).
        nodes = load_nodes()
        self.assertEqual(len(nodes), 8)
        self.assertEqual({n.id for n in nodes}, EXPECTED_IDS)

    def test_no_duplicate_ids(self):
        nodes = load_nodes()
        ids = [n.id for n in nodes]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_nodes_validate(self):
        ok, errors, _ = validate_all()
        self.assertTrue(ok, msg="\n".join(errors))

    def test_required_fields_present(self):
        for node in load_nodes():
            self.assertTrue(REQUIRED_FIELDS <= set(node.data), node.id)

    def test_relations_resolve_within_corpus(self):
        nodes = load_nodes()
        ids = {n.id for n in nodes}
        for node in nodes:
            relations = node.data.get("relations") or {}
            for key in ("related", "requires_consideration_of"):
                for target in relations.get(key, []) or []:
                    self.assertIn(target, ids, f"{node.id} -> {target}")

    def test_taxonomy_values_known(self):
        taxonomy = load_taxonomy()
        nodes = load_nodes()
        for node in nodes:
            self.assertIn(node.kind, taxonomy["node-kinds"])
            contexts = node.data.get("contexts") or {}
            for section in ("languages", "project_types", "lifecycle_stages"):
                for value in contexts.get(section, []) or []:
                    self.assertIn(value, taxonomy["contexts"][section], node.id)
            relations = node.data.get("relations") or {}
            for key in relations:
                self.assertIn(key, taxonomy["relation-types"])

    def test_hard_limits_hold(self):
        for node in load_nodes():
            data = node.data
            self.assertLessEqual(
                count_words(data["summary"]), SUMMARY_MAX_WORDS, node.id
            )
            for field, (lo, hi) in LIST_LIMITS.items():
                if field in data:
                    self.assertGreaterEqual(len(data[field]), lo, f"{node.id}.{field}")
                    self.assertLessEqual(len(data[field]), hi, f"{node.id}.{field}")
            for field in LIST_FIELDS:
                for entry in data.get(field, []) or []:
                    self.assertLessEqual(
                        count_words(entry), MAX_LIST_ENTRY_WORDS,
                        f"{node.id}.{field} entry: {entry!r}",
                    )
            self.assertLessEqual(count_words(data), MAX_NODE_WORDS, node.id)

    def test_no_future_candidate_lists(self):
        # The brief forbids any second list of future node candidates.
        nodes = load_nodes()
        for node in nodes:
            self.assertNotIn("candidates", node.data)
            self.assertNotIn("future", node.data)


if __name__ == "__main__":
    unittest.main()
