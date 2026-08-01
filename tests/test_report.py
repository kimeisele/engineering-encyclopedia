"""Application Report verification tests (Section 7 and Section 10).

Every rejection case from Section 10 is its own test, plus the positive
acceptance case and a pack-tamper case.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from encyclopedia.loader import load_nodes
from encyclopedia.pack import PackOptions, compose_pack
from encyclopedia.report import verify_report
from encyclopedia.retrieval import RetrievalIndex

E1 = "Write a worker that consumes jobs from a queue and charges a customer."


def make_pack(tmpdir: Path):
    nodes = load_nodes()
    index = RetrievalIndex(nodes)
    pack = compose_pack(nodes, index, E1, PackOptions())
    pack_path = tmpdir / "pack.yaml"
    pack_path.write_text(yaml.safe_dump(pack, sort_keys=True), encoding="utf-8")
    return nodes, pack, pack_path


def build_report(pack, nodes):
    """A well-formed report against *pack*: first pack node applied with all
    questions answered, every other pack node not_applied."""
    node_by_id = {n.id: n for n in nodes}
    pack_nodes = [
        entry
        for section in ("primary", "supporting")
        for entry in pack["context_pack"][section]
    ]
    first = pack_nodes[0]
    applied = [
        {
            "node": first["id"],
            "version": first["version"],
            "hash": first["hash"],
            "questions_answered": [
                {
                    "question": q,
                    "answer": "Recorded in the same transaction; verified in tests.",
                    "location": "tests/test_report.py:1",
                }
                for q in node_by_id[first["id"]].data["questions"]
            ],
            "unanswered": [],
        }
    ]
    not_applied = [
        {"node": entry["id"], "reason": "No code touched by this node in the diff."}
        for entry in pack_nodes[1:]
    ]
    return {
        "application_report": {
            "knowledge_revision": pack["knowledge_revision"],
            "context_pack_hash": pack["context_pack_hash"],
            "applied": applied,
            "not_applied": not_applied,
        }
    }


class TestVerifyReport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.nodes, self.pack, self.pack_path = make_pack(self.tmpdir)
        self.report = build_report(self.pack, self.nodes)
        self.report_path = self.tmpdir / "report.yaml"

    def tearDown(self):
        self._tmp.cleanup()

    def _write_and_verify(self, report=None):
        path = self.report_path
        path.write_text(yaml.safe_dump(report or self.report, sort_keys=True), encoding="utf-8")
        return verify_report(path, self.pack_path, self.nodes)

    def _mutate(self, mutator):
        report = yaml.safe_load(yaml.safe_dump(self.report))  # deep copy
        mutator(report)
        return report

    # -- positive case -----------------------------------------------------

    def test_accepts_well_formed_report(self):
        ok, failures = self._write_and_verify()
        self.assertTrue(ok, msg=failures)
        self.assertEqual(failures, [])

    # -- binding to the pack ------------------------------------------------

    def test_wrong_context_pack_hash_rejected(self):
        report = self._mutate(
            lambda r: r["application_report"].__setitem__("context_pack_hash", "000000000000")
        )
        ok, failures = self._write_and_verify(report)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "context_pack_hash_mismatch" for f in failures))

    def test_mismatched_knowledge_revision_rejected(self):
        report = self._mutate(
            lambda r: r["application_report"].__setitem__("knowledge_revision", "000000000000")
        )
        ok, failures = self._write_and_verify(report)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "knowledge_revision_mismatch" for f in failures))

    def test_omitted_pack_node_rejected(self):
        def mutate(r):
            entry = r["application_report"]["not_applied"].pop()
            del entry
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "omitted_pack_node" for f in failures))

    def test_report_node_absent_from_pack_rejected(self):
        absent = next(
            n.id for n in self.nodes
            if n.id not in {
                e["id"]
                for s in ("primary", "supporting")
                for e in self.pack["context_pack"][s]
            }
        )
        def mutate(r):
            r["application_report"]["not_applied"].append(
                {"node": absent, "reason": "extra"}
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "node_not_in_pack" for f in failures))

    def test_duplicated_disposition_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"].append(
                dict(r["application_report"]["not_applied"][0])
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_disposition" for f in failures))

    def test_node_under_both_dispositions_rejected(self):
        def mutate(r):
            first = r["application_report"]["applied"][0]["node"]
            r["application_report"]["not_applied"].append(
                {"node": first, "reason": "also not applied"}
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_disposition" for f in failures))

    def test_contradictory_question_disposition_rejected(self):
        # Review finding F1: the same question answered and unanswered is a
        # flat contradiction in the evidence.
        def mutate(r):
            applied = r["application_report"]["applied"][0]
            question = applied["questions_answered"][0]["question"]
            applied["unanswered"].append({"question": question, "reason": "not really"})
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "contradictory_disposition" for f in failures))

    def test_duplicate_question_rejected(self):
        def mutate(r):
            applied = r["application_report"]["applied"][0]
            applied["questions_answered"].append(
                dict(applied["questions_answered"][0])
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_question" for f in failures))

    # -- binding to the corpus ----------------------------------------------

    def test_unknown_node_id_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"].append(
                {"node": "no.such.node", "reason": "extra"}
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "unknown_node" for f in failures))
        self.assertTrue(any(f["code"] == "node_not_in_pack" for f in failures))

    def test_wrong_version_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["version"] += 1
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "wrong_version" for f in failures))

    def test_wrong_content_hash_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["hash"] = "deadbeef0000"
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "wrong_hash" for f in failures))

    # -- binding to the node content -----------------------------------------

    def test_altered_question_rejected(self):
        def mutate(r):
            qa = r["application_report"]["applied"][0]["questions_answered"][0]
            qa["question"] = qa["question"] + " and something else?"
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "altered_question" for f in failures))

    def test_omitted_question_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"].pop()
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "omitted_question" for f in failures))

    def test_empty_answer_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["answer"] = "   "
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "empty_answer" for f in failures))

    def test_answer_too_long_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["answer"] = (
                " ".join(["word"] * 41)
            )
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "answer_too_long" for f in failures))

    def test_empty_location_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["location"] = ""
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "empty_location" for f in failures))

    def test_empty_reason_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"][0]["reason"] = ""
        ok, failures = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "empty_reason" for f in failures))

    # -- pack tampering -------------------------------------------------------

    def test_tampered_pack_rejected(self):
        pack = yaml.safe_load(self.pack_path.read_text(encoding="utf-8"))
        pack["context_pack"]["primary"][0]["relevance"] = "tampered"
        tampered_path = self.tmpdir / "pack_tampered.yaml"
        tampered_path.write_text(yaml.safe_dump(pack, sort_keys=True), encoding="utf-8")
        report_path = self.tmpdir / "report.yaml"
        report_path.write_text(
            yaml.safe_dump(self.report, sort_keys=True), encoding="utf-8"
        )
        ok, failures = verify_report(report_path, tampered_path, self.nodes)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "pack_hash_mismatch" for f in failures))

    def test_missing_pack_is_hard_error(self):
        ok, failures = verify_report(self.report_path, self.tmpdir / "nope.yaml", self.nodes)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "unreadable" for f in failures))


if __name__ == "__main__":
    unittest.main()
