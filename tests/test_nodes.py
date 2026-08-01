"""Corpus tests: exactly sixteen nodes, schema rules, hard limits, relations,
taxonomy bindings (Sections 3 and 4 of the founding brief; corpus extended
from eight to sixteen nodes by owner decision, see docs/CORPUS_RULE.md and
DEVIATIONS D10-D13)."""

import unittest
from pathlib import Path

from encyclopedia.loader import load_nodes, load_taxonomy
from encyclopedia.validate import (
    ENTRY_WORD_CHECKED_FIELDS,
    LIST_LIMITS,
    MAX_LIST_ENTRY_WORDS,
    MAX_NODE_WORDS,
    SUMMARY_MAX_WORDS,
    validate_all,
    validate_node,
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
    "reliability.outbox-pattern",
    "performance.cache-invalidation",
    "testing.evaluation-contamination",
    "reliability.circuit-breaker",
    "reliability.dead-letter-queue",
    "observability.correlation-id",
    "concurrency.locking-strategy",
    "review.unsupported-claims",
}

REQUIRED_FIELDS = {
    "id", "version", "title", "kind", "status", "summary", "intent_signals",
    "applies_when", "does_not_imply", "questions", "risks", "provenance",
    "keywords",
}

# every list-valued field whose entries must stay <= MAX_LIST_ENTRY_WORDS —
# imported from the validator so the two can never disagree
LIST_FIELDS = ENTRY_WORD_CHECKED_FIELDS


class TestCorpus(unittest.TestCase):
    def test_exactly_sixteen_nodes(self):
        # The count is asserted: a short corpus fails rather than lowering
        # the expectation (Section 10). Raised 8 -> 10 -> 11 -> 15 -> 16 by
        # owner decision — an intentional corpus change (docs/CORPUS_RULE.md,
        # DEVIATIONS D10/D11/D12/D13), not a weakened test.
        nodes = load_nodes()
        self.assertEqual(len(nodes), 16)
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

    # -- validator soundness (review findings F3/F4) -------------------------

    @staticmethod
    def _mutant(base, **changes):
        from encyclopedia.loader import Node

        data = dict(base.data)
        data.update(changes)
        return Node(
            id=base.id, version=data.get("version"), title=base.title,
            kind=base.kind, status=base.status, data=data,
            content_hash="x" * 12, path=base.path,
        )

    def test_validator_checks_every_list_field_for_word_limit(self):
        nodes = load_nodes()
        taxonomy = load_taxonomy()
        ids = {n.id for n in nodes}
        for field in ("applies_when", "does_not_apply_when", "keywords"):
            mutant = self._mutant(nodes[0], **{field: ["word " * 30]})
            errors = validate_node(mutant, ids, taxonomy)
            self.assertTrue(
                any(field in e and "exceeds" in e for e in errors), f"{field}: {errors}"
            )

    def test_string_version_rejected(self):
        nodes = load_nodes()
        taxonomy = load_taxonomy()
        ids = {n.id for n in nodes}
        mutant = self._mutant(nodes[0], version="1")
        errors = validate_node(mutant, ids, taxonomy)
        self.assertTrue(any("version must be an integer" in e for e in errors))

    def test_non_numeric_version_is_clean_failure_not_crash(self):
        import tempfile
        from pathlib import Path

        from encyclopedia import loader

        with tempfile.TemporaryDirectory() as td:
            bad_dir = Path(td)
            (bad_dir / "bad.yaml").write_text(
                "id: test.bad\n"
                "version: one\n"
                "title: Bad\n"
                "kind: principle\n"
                "status: established\n",
                encoding="utf-8",
            )
            loaded = loader.load_nodes(bad_dir)
            self.assertEqual(loaded[0].version, "one")  # raw, no coercion
        # validation surfaces a clean error, no exception
        mutant = self._mutant(load_nodes()[0], version="one")
        taxonomy = load_taxonomy()
        errors = validate_node(mutant, {n.id for n in load_nodes()}, taxonomy)
        self.assertTrue(any("version must be an integer" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
