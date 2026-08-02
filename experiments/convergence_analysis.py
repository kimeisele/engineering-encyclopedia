#!/usr/bin/env python3
"""Reproduce every table in docs/CONVERGENCE_ANALYSIS.md from the fixtures.

One command:  python3 experiments/convergence_analysis.py
Output: the four reports (between-provider gap, within-arm sd, structural
markers, criterion-level modal agreement) in the same shape as the
document, so the committed numbers can be verified cell by cell.

Marker regexes are exactly the ones published in the document's
"Structural markers (exact definitions)" section. Scoring uses
runner.score_code with the repaired instrument (extraction + comment
stripping; extraction only for e6's prose).
"""

from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import runner  # noqa: E402

# (task, ds_fixtures, mr_fixtures, n, has_placebo_in_separate_dir)
TASKS = {
    "e1": ("experiments/fixtures-corrected", "experiments/fixtures-mistral", 5, True),
    "e2": ("experiments/fixtures-corrected", "experiments/fixtures-mistral", 5, True),
    "e3": ("experiments/fixtures-corrected", "experiments/fixtures-mistral", 5, True),
    "e4": ("experiments/fixtures-oos-ds", "experiments/fixtures-oos-mistral", 15, False),
    "e5": ("experiments/fixtures-oos-ds", "experiments/fixtures-oos-mistral", 15, False),
    "e6": ("experiments/fixtures-e6-ds", "experiments/fixtures-e6-mistral", 5, False),
}
PLACEBO_DIRS = {
    t: ("experiments/fixtures-placebo", "experiments/fixtures-placebo-mistral")
    for t in ("e1", "e2", "e3")
}

# Exact markers from CONVERGENCE_ANALYSIS.md, "Structural markers (exact definitions)".
MARKERS = {
    "e1": {
        "dedup_record": r"processed|done|handled|dedup",
        "check_before": r"if\s+.*(processed|exists|already|done)",
        "same_tx": r"transaction|atomic|unique|ON CONFLICT|conflict",
    },
    "e2": {
        "argv_list": r"\.(run|Popen|call|check_output|check_call)\s*\(\s*(\[|[A-Za-z_]\w*\s*[,)])",
        "validation": r"re\.(match|fullmatch|search)|startswith|valid|whitelist|allowed|safe|branches",
    },
    "e3": {
        "temp_file": r"tempfile|mkstemp|NamedTemporaryFile|\.tmp|\btmp",
        "atomic_rename": r"os\.replace|os\.rename|Path\.replace",
        "fsync": r"\.flush\s*\(|os\.fsync|fsync",
    },
    "e4": {
        "named_states": r"closed|open|half[- ]?open|is_open|CLOSED|OPEN",
        "threshold": r"max_failures|failure_threshold|threshold|failures\s*[>=]",
        "reset_path": r"state\s*=\s*['\"]closed|_reset\s*\(|CLOSED|failures\s*=\s*0",
        "fail_fast": r"if\s+.*(is_open|state|circuit).{0,40}(raise|return|fail)",
    },
    "e5": {
        "id_parameter": r"correlation_id|request_id|trace_id",
        "id_header": r"X-Request-Id|x-request-id|headers",
    },
    "e6": {
        "file_line_cited": r"worker\.py\s*[:@]\s*\d+|\blines?\s+\d+",
        "unsupported_phrasing": r"not supported|unsupported",
    },
}


def _path(task: str, prov: str, arm: str, k: int, e6: bool) -> Path:
    if e6:
        return Path(prov) / arm / f"run-{k}.txt"
    return Path(prov) / task / arm / f"run-{k}.txt"


def cell(task: str, arm: str) -> tuple[list, list]:
    """(ds_scores, mr_scores) for one task/arm cell."""
    ds, mr, n, separate = TASKS[task]
    e6 = task == "e6"
    if separate and arm == "placebo":
        ds, mr = PLACEBO_DIRS[task]
        n = 5
    out = []
    for prov in (ds, mr):
        scores = []
        for k in range(1, n + 1):
            p = _path(task, prov, arm, k, e6)
            if not p.is_file():
                continue
            code = p.read_text(encoding="utf-8")
            scores.append(runner.score_code(task, code)["score"])
        out.append(scores)
    return out[0], out[1]


def _artifact(task: str, prov: str, arm: str, k: int, e6: bool) -> str:
    code = _path(task, prov, arm, k, e6).read_text(encoding="utf-8")
    if e6:
        return runner.extract_artifact(code)
    return runner.strip_comments(runner.extract_artifact(code))


def report_1() -> None:
    print("=== REPORT 1: between-provider gap (|mean_DS - mean_MR|) ===")
    print(f"{'task':4s} {'arm':10s} {'DS':>6s} {'MR':>6s} {'gap':>6s}")
    for task in TASKS:
        for arm in ("control", "treatment", "placebo"):
            d, m = cell(task, arm)
            if not d or not m:
                continue
            dm, mm = statistics.mean(d), statistics.mean(m)
            print(f"{task:4s} {arm:10s} {dm:6.2f} {mm:6.2f} {abs(dm-mm):6.2f}")


def report_2() -> None:
    print("\n=== REPORT 2: within-arm sd per cell ===")
    print(f"{'task':4s} {'arm':10s} {'DS sd':>6s} {'MR sd':>6s}")
    for task in TASKS:
        for arm in ("control", "treatment", "placebo"):
            d, m = cell(task, arm)
            if not d or not m:
                continue
            ds_sd = statistics.stdev(d) if len(d) > 1 else 0.0
            mr_sd = statistics.stdev(m) if len(m) > 1 else 0.0
            print(f"{task:4s} {arm:10s} {ds_sd:6.2f} {mr_sd:6.2f}")


def report_3() -> None:
    print("\n=== REPORT 3: structural markers (mean |rate_DS - rate_MR|) ===")
    print(f"{'task':4s} {'arm':10s} {'marker-diff':>11s}   marker detail (DS/MR)")
    for task in TASKS:
        ds, mr, n, separate = TASKS[task]
        e6 = task == "e6"
        for arm in ("control", "treatment", "placebo"):
            pds, pmr = ds, mr
            nn = n
            if separate and arm == "placebo":
                pds, pmr = PLACEBO_DIRS[task]
                nn = 5
            rates = {}
            for marker, pat in MARKERS[task].items():
                dc = sum(
                    1
                    for k in range(1, nn + 1)
                    if re.search(pat, _artifact(task, pds, arm, k, e6), re.DOTALL)
                )
                mc = sum(
                    1
                    for k in range(1, nn + 1)
                    if re.search(pat, _artifact(task, pmr, arm, k, e6), re.DOTALL)
                )
                rates[marker] = (dc / nn, mc / nn)
            md = sum(abs(d - m) for d, m in rates.values()) / len(rates)
            detail = "  ".join(
                f"{m}:{d:.0%}/{r:.0%}" for m, (d, r) in rates.items()
            )
            print(f"{task:4s} {arm:10s} {md:11.2f}   {detail}")


def report_4() -> None:
    print("\n=== REPORT 4: criterion-level modal agreement (disagreements / total) ===")
    print(f"{'task':4s} {'arm':10s} {'disagree':>8s}")
    for task in TASKS:
        ds, mr, n, separate = TASKS[task]
        e6 = task == "e6"
        total = len(runner.rubric_for(task)["criteria"])
        for arm in ("control", "treatment", "placebo"):
            pds, pmr = ds, mr
            nn = n
            if separate and arm == "placebo":
                pds, pmr = PLACEBO_DIRS[task]
                nn = 5
            criteria = []
            for prov in (pds, pmr):
                prov_crit = []
                for k in range(1, nn + 1):
                    code = _path(task, prov, arm, k, e6).read_text(encoding="utf-8")
                    prov_crit.append(
                        {c["id"]: c["satisfied"] for c in runner.score_code(task, code)["criteria"]}
                    )
                criteria.append(prov_crit)
            disagree = 0
            for cid in [c["id"] for c in runner.rubric_for(task)["criteria"]]:
                dm = sum(1 for r in criteria[0] if r[cid]) >= len(criteria[0]) / 2
                mm = sum(1 for r in criteria[1] if r[cid]) >= len(criteria[1]) / 2
                if dm != mm:
                    disagree += 1
            print(f"{task:4s} {arm:10s} {disagree:8d}/{total}")


if __name__ == "__main__":
    report_1()
    report_2()
    report_3()
    report_4()
