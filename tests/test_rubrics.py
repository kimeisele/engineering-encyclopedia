"""Rubric self-test: the rubrics' own regression suite.

For every criterion of every rubric in ``experiments/rubrics/`` there must be
a positive fixture (a snippet that must satisfy the criterion) and a negative
fixture (a snippet that must not). The method-definition case found in the
out-of-sample diagnosis (``log_success(self, trace_id, ...)`` satisfying
``id_in_logs``) is pinned as a negative fixture here.

The test mirrors ``runner.score_code``: a present-criterion is satisfied iff
its pattern matches (re.search, DOTALL); an absent-criterion iff it does not.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import runner  # noqa: E402

FIXTURES = {
    "e1": {
        "operation_identity": {
            "positive": "job_id = job['id']",
            "negative": "def process(job):\n    charge(job)",
        },
        "dedup_record": {
            "positive": "processed_set.add(job_id)",
            "negative": "def process(job):\n    charge(job)",
        },
        "check_before_effect": {
            "positive": "if job_id in processed_ids:\n    return",
            "negative": "charge(job)",
        },
        "effect_guarded_by_record": {
            "positive": "with db.transaction():\n    insert(processed, job_id)\n    charge(job)",
            "negative": "charge(job)\nrecord(job_id)",
        },
        "no_timestamp_key": {
            "positive": "key = job['id']",
            "negative": "key = str(time.time())",
        },
        "durable_record": {
            "positive": "sqlite3.connect('jobs.db')",
            "negative": "processed = set()",
        },
    },
    "e2": {
        "no_shell_true": {
            "positive": "subprocess.run(['git', 'branch', branch])",
            "negative": "subprocess.run(cmd, shell=True)",
        },
        "argv_list": {
            "positive": "subprocess.run(['git', 'branch', branch])",
            "negative": "subprocess.run('git branch ' + branch)",
        },
        "branch_as_data": {
            "positive": "subprocess.run(['git', 'branch', branch_name])",
            "negative": "subprocess.run('git branch ' + branch_name)",
        },
        "no_command_interpolation": {
            "positive": "subprocess.run(['git', 'checkout', branch])",
            "negative": "subprocess.run(f'git checkout {branch}')",
        },
        "validation_or_whitelist": {
            "positive": "if not re.match(r'^[a-z0-9-]+$', branch):\n    raise ValueError()",
            "negative": "subprocess.run(['git', 'checkout', branch])",
        },
        "no_os_system": {
            "positive": "subprocess.run(['git', 'checkout', branch])",
            "negative": "os.system('git checkout ' + branch)",
        },
    },
    "e3": {
        "temp_file": {
            "positive": "tempfile.NamedTemporaryFile(dir=os.path.dirname(path))",
            "negative": "open(path, 'w')",
        },
        "atomic_rename": {
            "positive": "os.replace(tmp, path)",
            "negative": "content.replace('a', 'b')",
        },
        "no_direct_truncate": {
            "positive": "os.replace(tmp, path)",
            "negative": "open(path, 'w')",
        },
        "flush_or_fsync": {
            "positive": "f.flush()\nos.fsync(f.fileno())",
            "negative": "os.replace(tmp, path)",
        },
        "same_directory": {
            "positive": "tempfile.NamedTemporaryFile(dir=os.path.dirname(path))",
            "negative": "tempfile.NamedTemporaryFile(dir='/tmp')",
        },
        "failure_cleanup": {
            "positive": "try:\n    write()\nexcept Exception:\n    os.unlink(tmp)",
            "negative": "os.replace(tmp, path)",
        },
    },
    "e4": {
        "breaker_state": {
            "positive": "if self.is_open:",
            "negative": "with open(f) as fh:",
        },
        "failure_threshold": {
            "positive": "if failures >= max_failures:",
            "negative": "requests.post(url)",
        },
        "fail_fast_when_open": {
            "positive": "if self.is_open:\n    raise ServiceUnavailable()",
            "negative": "with open(f) as fh:",
        },
        "recovery_probe": {
            "positive": "time.sleep(cooldown)",
            "negative": "requests.post(url)",
        },
        "success_resets": {
            "positive": "self.state = 'closed'",
            "negative": "self.reset_timeout = 30",
        },
        "no_unbounded_loop": {
            "positive": "if retry_count <= max_retries:",
            "negative": "while True:\n    call()",
        },
    },
    "e5": {
        "id_generated": {
            "positive": "correlation_id = str(uuid.uuid4())",
            "negative": "def handle(request):\n    pass",
        },
        "id_propagated": {
            "positive": "headers['X-Request-Id'] = correlation_id",
            "negative": "logger.error('failed')",
        },
        "downstream_reuses": {
            "positive": "correlation_id = request.correlation_id",
            "negative": "correlation_id = str(uuid.uuid4())",
        },
        "id_in_logs": {
            # the method-definition case from the diagnosis must NOT satisfy
            "positive": "self.logger.error('failed', extra={'correlation_id': cid})",
            "negative": "def log_success(self, trace_id: str):\n    pass",
        },
        "errors_carry_id": {
            "positive": "error_context = {'correlation_id': cid}\nwrapped.__dict__.update(error_context)",
            "negative": "logger.error('failed')",
        },
        "no_idempotency_conflation": {
            "positive": "correlation_id = request.correlation_id",
            "negative": "idempotency_key = correlation_id",
        },
    },
    "e6": {
        "claims_located": {
            "positive": "the report claims X at worker.py:41",
            "negative": "the report claims X",
        },
        "raw_output_cited": {
            "positive": "the raw output shows the charge at line 12",
            "negative": "the report describes the charge",
        },
        "order_parts_addressed": {
            "positive": "the order part about retries is unaddressed",
            "negative": "the implementation is correct",
        },
        "alternatives_excluded": {
            "positive": "another explanation, a stale cache, was not excluded",
            "negative": "the cause is the retry loop",
        },
        "contradictions_checked": {
            "positive": "this contradicts the earlier decision on retries",
            "negative": "the retry loop is fine",
        },
        "no_attitude_only": {
            "positive": "the claim is at line 7 of the output",
            "negative": "I think the review is thorough and careful",
        },
    },
}


def _criterion_satisfied(criterion, snippet: str) -> bool:
    artifact = runner.strip_comments(snippet)
    matched = re.search(criterion["pattern"], artifact, re.DOTALL) is not None
    return matched if criterion["kind"] == "present" else not matched


class TestRubricSelfTest(unittest.TestCase):
    def test_every_criterion_has_fixtures(self):
        for task in runner.RUBRIC_FILES:
            rubric = runner.rubric_for(task)
            for criterion in rubric["criteria"]:
                fixtures = FIXTURES.get(task, {}).get(criterion["id"])
                self.assertIsNotNone(
                    fixtures, f"{task}/{criterion['id']} has no fixtures"
                )
                self.assertIn("positive", fixtures)
                self.assertIn("negative", fixtures)

    def test_positive_fixtures_satisfy(self):
        for task in runner.RUBRIC_FILES:
            rubric = runner.rubric_for(task)
            for criterion in rubric["criteria"]:
                snippet = FIXTURES[task][criterion["id"]]["positive"]
                self.assertTrue(
                    _criterion_satisfied(criterion, snippet),
                    f"{task}/{criterion['id']}: positive fixture must satisfy",
                )

    def test_negative_fixtures_do_not_satisfy(self):
        for task in runner.RUBRIC_FILES:
            rubric = runner.rubric_for(task)
            for criterion in rubric["criteria"]:
                snippet = FIXTURES[task][criterion["id"]]["negative"]
                self.assertFalse(
                    _criterion_satisfied(criterion, snippet),
                    f"{task}/{criterion['id']}: negative fixture must not satisfy",
                )

    def test_no_unexpected_extra_fixtures(self):
        # every fixture entry must name a real criterion
        for task, criteria in FIXTURES.items():
            self.assertIn(task, runner.RUBRIC_FILES)
            ids = {c["id"] for c in runner.rubric_for(task)["criteria"]}
            for cid in criteria:
                self.assertIn(cid, ids, f"{task}/{cid} is not a criterion")


if __name__ == "__main__":
    unittest.main()
