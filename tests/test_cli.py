"""CLI smoke tests: every command, exit codes, YAML and JSON output, and a
query -> verify-report round trip."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from encyclopedia.cli import main
from encyclopedia.loader import load_nodes
from encyclopedia.pack import PackOptions, compose_pack
from encyclopedia.retrieval import RetrievalIndex

QUERY = "make sure this worker doesn't process the same job twice"


def run_cli(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


class TestCli(unittest.TestCase):
    def test_validate_ok(self):
        code, out = run_cli(["validate"])
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)

    def test_list_yaml(self):
        code, out = run_cli(["list"])
        self.assertEqual(code, 0)
        data = yaml.safe_load(out)
        self.assertEqual(len(data), 30)
        self.assertEqual(data[0]["id"], "apis.http-status-semantics")  # sorted

    def test_list_json(self):
        code, out = run_cli(["list", "--format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(len(data), 30)

    def test_show_ok_and_unknown(self):
        code, out = run_cli(["show", "reliability.idempotency"])
        self.assertEqual(code, 0)
        data = yaml.safe_load(out)
        self.assertEqual(data["id"], "reliability.idempotency")
        self.assertIn("content_hash", data)
        code, _ = run_cli(["show", "no.such.node"])
        self.assertEqual(code, 1)

    def test_search_ranks_idempotency_first(self):
        code, out = run_cli(["search", "duplicate processing"])
        self.assertEqual(code, 0)
        data = yaml.safe_load(out)
        self.assertEqual(data[0]["id"], "reliability.idempotency")

    def test_related(self):
        code, out = run_cli(["related", "reliability.idempotency"])
        self.assertEqual(code, 0)
        data = yaml.safe_load(out)
        ids = {d["id"] for d in data}
        self.assertIn("reliability.retry-semantics", ids)
        self.assertIn("concurrency.race-conditions", ids)

    def test_query_json_and_verify_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            code, out = run_cli(["query", QUERY, "--format", "json"])
            self.assertEqual(code, 0)
            pack = json.loads(out)
            self.assertIn("context_pack_hash", pack)
            pack_path = tmp / "pack.json"
            pack_path.write_text(out, encoding="utf-8")

            # build a valid report against this pack
            nodes = load_nodes()
            node_by_id = {n.id: n for n in nodes}
            pack_nodes = [
                e for s in ("primary", "supporting")
                for e in pack["context_pack"][s]
            ]
            first = pack_nodes[0]
            report = {
                "application_report": {
                    "knowledge_revision": pack["knowledge_revision"],
                    "context_pack_hash": pack["context_pack_hash"],
                    "applied": [{
                        "node": first["id"],
                        "version": first["version"],
                        "hash": first["hash"],
                        "questions_answered": [
                            {"question": q, "answer": "verified by unit test",
                             "location": "tests/test_cli.py"}
                            for q in node_by_id[first["id"]].data["questions"]
                        ],
                        "unanswered": [],
                    }],
                    "not_applied": [
                        {"node": e["id"], "reason": "not touched by this change"}
                        for e in pack_nodes[1:]
                    ],
                }
            }
            report_path = tmp / "report.json"
            report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")

            code, out = run_cli(
                ["verify-report", str(report_path), "--pack", str(pack_path), "--format", "json"]
            )
            self.assertEqual(code, 0, out)
            self.assertTrue(json.loads(out)["ok"])

            # now break it: wrong pack hash
            report["application_report"]["context_pack_hash"] = "000000000000"
            report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
            code, out = run_cli(
                ["verify-report", str(report_path), "--pack", str(pack_path)]
            )
            self.assertEqual(code, 1)
            result = yaml.safe_load(out)
            self.assertFalse(result["ok"])
            self.assertTrue(any(
                f["code"] == "context_pack_hash_mismatch" for f in result["failures"]
            ))

    def test_query_detail_and_caps(self):
        code, out = run_cli(["query", QUERY, "--detail", "full", "--max-primary", "9"])
        self.assertEqual(code, 0)
        pack = yaml.safe_load(out)
        self.assertLessEqual(len(pack["context_pack"]["primary"]), 3)

    def test_unknown_command_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(["frobnicate"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
