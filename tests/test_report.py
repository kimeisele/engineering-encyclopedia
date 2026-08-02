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

    def _write_and_verify(self, report=None, nodes=None):
        path = self.report_path
        path.write_text(yaml.safe_dump(report or self.report, sort_keys=True), encoding="utf-8")
        return verify_report(path, self.pack_path, nodes if nodes is not None else self.nodes)

    def _mutate(self, mutator):
        report = yaml.safe_load(yaml.safe_dump(self.report))  # deep copy
        mutator(report)
        return report

    # -- positive case -----------------------------------------------------

    def test_accepts_well_formed_report(self):
        ok, failures, corpus = self._write_and_verify()
        self.assertTrue(ok, msg=failures)
        self.assertEqual(failures, [])
        self.assertEqual(corpus["status"], "current")

    # -- binding to the pack ------------------------------------------------

    def test_wrong_context_pack_hash_rejected(self):
        report = self._mutate(
            lambda r: r["application_report"].__setitem__("context_pack_hash", "000000000000")
        )
        ok, failures, _corpus = self._write_and_verify(report)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "context_pack_hash_mismatch" for f in failures))

    def test_mismatched_knowledge_revision_rejected(self):
        report = self._mutate(
            lambda r: r["application_report"].__setitem__("knowledge_revision", "000000000000")
        )
        ok, failures, _corpus = self._write_and_verify(report)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "knowledge_revision_mismatch" for f in failures))

    def test_omitted_pack_node_rejected(self):
        def mutate(r):
            entry = r["application_report"]["not_applied"].pop()
            del entry
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
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
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "node_not_in_pack" for f in failures))

    def test_duplicated_disposition_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"].append(
                dict(r["application_report"]["not_applied"][0])
            )
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_disposition" for f in failures))

    def test_node_under_both_dispositions_rejected(self):
        def mutate(r):
            first = r["application_report"]["applied"][0]["node"]
            r["application_report"]["not_applied"].append(
                {"node": first, "reason": "also not applied"}
            )
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_disposition" for f in failures))

    def test_contradictory_question_disposition_rejected(self):
        # Review finding F1: the same question answered and unanswered is a
        # flat contradiction in the evidence.
        def mutate(r):
            applied = r["application_report"]["applied"][0]
            question = applied["questions_answered"][0]["question"]
            applied["unanswered"].append({"question": question, "reason": "not really"})
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "contradictory_disposition" for f in failures))

    def test_duplicate_question_rejected(self):
        def mutate(r):
            applied = r["application_report"]["applied"][0]
            applied["questions_answered"].append(
                dict(applied["questions_answered"][0])
            )
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "duplicate_question" for f in failures))

    # -- binding to the corpus ----------------------------------------------

    def test_unknown_node_id_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"].append(
                {"node": "no.such.node", "reason": "extra"}
            )
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "node_not_in_pack" for f in failures))
        self.assertFalse(any(f["code"] == "unknown_node" for f in failures))

    # -- binding to the corpus (Slice 2: pack is primary truth) ---------------

    def test_old_pack_verifies_after_corpus_grows(self):
        # A pack composed against a subset corpus (an "old" corpus) must stay
        # verifiable when verified against the grown corpus: the report is
        # bound to the pack, and the corpus cross-check reports stale
        # non-fatally instead of failing.
        old_ids = [
            "reliability.idempotency",
            "reliability.retry-semantics",
            "concurrency.race-conditions",
            "python.files.atomic-replacement",
            "python.processes.subprocess-safety",
        ]
        old_nodes = [n for n in load_nodes() if n.id in old_ids]
        old_index = RetrievalIndex(old_nodes)
        old_pack = compose_pack(old_nodes, old_index, E1, PackOptions())
        old_pack_path = self.tmpdir / "old_pack.yaml"
        old_pack_path.write_text(
            yaml.safe_dump(old_pack, sort_keys=True), encoding="utf-8"
        )
        old_report = build_report(old_pack, old_nodes)
        old_report_path = self.tmpdir / "old_report.yaml"
        old_report_path.write_text(
            yaml.safe_dump(old_report, sort_keys=True), encoding="utf-8"
        )
        # verify against the full, grown corpus
        ok, failures, corpus = verify_report(
            old_report_path, old_pack_path, load_nodes()
        )
        self.assertTrue(ok, msg=failures)
        self.assertEqual(failures, [])
        self.assertEqual(corpus["status"], "stale")
        self.assertTrue(any("corpus has moved on" in d for d in corpus["details"]))

    def test_edited_node_pack_still_verifies_against_pack_questions(self):
        # A pack whose node has since been edited (different questions,
        # version, hash) verifies against the pack's recorded questions —
        # not against the current corpus — and reports corpus drift
        # non-fatally.
        nodes = load_nodes()
        index = RetrievalIndex(nodes)
        pack = compose_pack(nodes, index, E1, PackOptions())
        pack_path = self.tmpdir / "pack.yaml"
        pack_path.write_text(yaml.safe_dump(pack, sort_keys=True), encoding="utf-8")
        report = build_report(pack, nodes)
        report_path = self.tmpdir / "report.yaml"
        report_path.write_text(yaml.safe_dump(report, sort_keys=True), encoding="utf-8")

        first_id = pack["context_pack"]["primary"][0]["id"]
        edited = self._edited_node(next(n for n in nodes if n.id == first_id))
        edited_corpus = [
            edited if n.id == first_id else n for n in nodes
        ]
        ok, failures, corpus = verify_report(report_path, pack_path, edited_corpus)
        self.assertTrue(ok, msg=failures)
        self.assertEqual(failures, [])
        # the edited corpus has a different revision, so the cross-check is
        # stale (a per-node "drifted" report is unreachable by construction:
        # any node edit changes corpus_revision, and report.knowledge_revision
        # must equal the pack's)
        self.assertEqual(corpus["status"], "stale")
        self.assertTrue(
            any("corpus has moved on" in d for d in corpus["details"])
        )

        # and an answer to a question from the EDITED node (not in the pack)
        # is still rejected — questions bind to the pack, not the corpus
        report2 = yaml.safe_load(yaml.safe_dump(report))
        edited_question = edited.data["questions"][-1]
        report2["application_report"]["applied"][0]["questions_answered"].append(
            {
                "question": edited_question,
                "answer": "from the edited corpus",
                "location": "tests/test_report.py:1",
            }
        )
        report_path.write_text(
            yaml.safe_dump(report2, sort_keys=True), encoding="utf-8"
        )
        ok2, failures2, _c = verify_report(report_path, pack_path, edited_corpus)
        self.assertFalse(ok2)
        self.assertTrue(any(f["code"] == "altered_question" for f in failures2))

    @staticmethod
    def _edited_node(base):
        from encyclopedia.canonical import node_content_hash
        from encyclopedia.loader import Node

        data = dict(base.data)
        data["questions"] = list(data.get("questions", []) or []) + [
            "A question only the edited corpus has?"
        ]
        data["version"] = int(data.get("version", 1)) + 1
        return Node(
            id=base.id,
            version=data["version"],
            title=base.title,
            kind=base.kind,
            status=base.status,
            data=data,
            content_hash=node_content_hash(data),
            path=base.path,
        )

    def test_wrong_version_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["version"] += 1
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "wrong_version" for f in failures))

    def test_wrong_content_hash_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["hash"] = "deadbeef0000"
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "wrong_hash" for f in failures))

    # -- binding to the node content -----------------------------------------

    def test_altered_question_rejected(self):
        def mutate(r):
            qa = r["application_report"]["applied"][0]["questions_answered"][0]
            qa["question"] = qa["question"] + " and something else?"
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "altered_question" for f in failures))

    def test_omitted_question_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"].pop()
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "omitted_question" for f in failures))

    def test_empty_answer_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["answer"] = "   "
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "empty_answer" for f in failures))

    def test_answer_too_long_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["answer"] = (
                " ".join(["word"] * 41)
            )
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "answer_too_long" for f in failures))

    def test_empty_location_rejected(self):
        def mutate(r):
            r["application_report"]["applied"][0]["questions_answered"][0]["location"] = ""
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "empty_location" for f in failures))

    def test_empty_reason_rejected(self):
        def mutate(r):
            r["application_report"]["not_applied"][0]["reason"] = ""
        ok, failures, _corpus = self._write_and_verify(self._mutate(mutate))
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
        ok, failures, _corpus = verify_report(report_path, tampered_path, self.nodes)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "pack_hash_mismatch" for f in failures))

    def test_missing_pack_is_hard_error(self):
        ok, failures, _corpus = verify_report(self.report_path, self.tmpdir / "nope.yaml", self.nodes)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "unreadable" for f in failures))

    # -- untrusted-YAML denial guards ----------------------------------------

    def test_oversized_report_rejected_cleanly(self):
        # > 2 MiB report must fail with a clean error, not exhaust memory.
        self.report_path.write_text("x" * (2 * 1024 * 1024 + 1), encoding="utf-8")
        ok, failures, _corpus = verify_report(self.report_path, self.pack_path, self.nodes)
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "unreadable" for f in failures))

    def test_deeply_nested_report_rejected_cleanly(self):
        # deep nesting must surface as a clean validation failure, not an
        # uncaught RecursionError traceback.
        self.report_path.write_text("[" * 10_000 + "]" * 10_000, encoding="utf-8")
        ok, failures, _corpus = verify_report(self.report_path, self.pack_path, self.nodes)
        self.assertFalse(ok)
        codes = [f["code"] for f in failures]
        self.assertTrue(any(c in ("unreadable", "invalid_yaml") for c in codes), codes)

    # -- mechanical --root location checks (Slice 3) --------------------------

    def _verify_with_root(self, report=None):
        root = self.tmpdir / "root"
        (root / "sub").mkdir(parents=True, exist_ok=True)
        (root / "worker.py").write_text(
            "\n".join(f"line {i}" for i in range(1, 50)), encoding="utf-8"
        )
        (root / "sub" / "deep.py").write_text("x\ny\nz\n", encoding="utf-8")
        report = report or yaml.safe_load(yaml.safe_dump(self.report))
        path = self.tmpdir / "root_report.yaml"
        path.write_text(yaml.safe_dump(report, sort_keys=True), encoding="utf-8")
        return verify_report(path, self.pack_path, self.nodes, root=root)

    def _set_locations(self, locations):
        report = yaml.safe_load(yaml.safe_dump(self.report))
        qa = report["application_report"]["applied"][0]["questions_answered"]
        for i, location in enumerate(locations):
            qa[i]["location"] = location
        return report

    def test_root_accepts_valid_locations(self):
        ok, failures, _ = self._verify_with_root(
            self._set_locations(
                ["worker.py:3", "worker.py:3-48", "sub/deep.py:2", "worker.py:49"]
            )
        )
        self.assertTrue(ok, msg=failures)
        self.assertEqual(failures, [])

    def test_root_rejects_bad_format(self):
        ok, failures, _ = self._verify_with_root(self._set_locations(["worker.py"]))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "location_format" for f in failures))

    def test_root_rejects_path_traversal(self):
        ok, failures, _ = self._verify_with_root(
            self._set_locations(["../secrets.py:1"])
        )
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "location_traversal" for f in failures))

    def test_root_rejects_absolute_path(self):
        ok, failures, _ = self._verify_with_root(
            self._set_locations(["/etc/passwd:1"])
        )
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "location_traversal" for f in failures))

    def test_root_rejects_missing_file(self):
        ok, failures, _ = self._verify_with_root(self._set_locations(["nope.py:1"]))
        self.assertFalse(ok)
        self.assertTrue(any(f["code"] == "location_file_missing" for f in failures))

    def test_root_rejects_out_of_range_line(self):
        ok, failures, _ = self._verify_with_root(self._set_locations(["worker.py:99"]))
        self.assertFalse(ok)
        self.assertTrue(
            any(f["code"] == "location_line_out_of_range" for f in failures)
        )

    def test_root_checks_every_answered_location(self):
        # fixing only the first location must not pass: every answered
        # location is checked, and the rest still resolve outside the root
        report = self._set_locations(["worker.py:1"])
        ok, failures, _ = self._verify_with_root(report)
        self.assertFalse(ok)
        self.assertTrue(
            any(f["code"] == "location_file_missing" for f in failures)
        )


if __name__ == "__main__":
    unittest.main()
