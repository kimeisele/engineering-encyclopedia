#!/usr/bin/env python3
"""Provider-agnostic experiment runner (Section 8 of the founding brief).

The concrete model command comes from the ENCYCLOPEDIA_RUNNER environment
variable: a shell command that reads the prompt on stdin and writes the
model's completion to stdout. No vendor name appears in code, config or
docs.

This harness is invoked manually. It is NOT part of unittest, NOT part of
CI, and NOT imported by the src/ package. The Section 1 network ban applies
to the query path only; this harness MAY use the network (the provider
command decides). Keep the two apart.

Usage:
  runner.py prompt <task> <arm>            print the prompt for one run
  runner.py run <task> <arm> <output>      invoke $ENCYCLOPEDIA_RUNNER,
                                           save the completion, log a manifest
  runner.py score <task> <code-file>       score recorded output with the rubric
  runner.py summarize <fixtures-dir>       write the results table (RESULTS.md)

Arms: control (task prompt only) and treatment (task + context pack + the
instruction to return an Application Report). Five runs per arm, ten per
task, thirty in total. Recorded fixtures may be included only when they are
genuine outputs of an identified external agent run, with model and date
noted in the manifest; never hand-author synthetic fixtures.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]  # repository root
TASKS_DIR = ROOT / "experiments" / "tasks"
RUBRICS_DIR = ROOT / "experiments" / "rubrics"
PACKS_DIR = ROOT / "experiments" / "packs"
DEFAULT_FIXTURES = ROOT / "experiments" / "fixtures"

RUBRIC_FILES = {
    "e1": "e1_idempotency.yaml",
    "e2": "e2_subprocess_safety.yaml",
    "e3": "e3_atomic_replacement.yaml",
}

ARMS = ("control", "treatment")


def prompt_for(task: str, arm: str) -> str:
    path = TASKS_DIR / f"{task}-{arm}.txt"
    return path.read_text(encoding="utf-8")


def rubric_for(task: str) -> Dict[str, Any]:
    path = RUBRICS_DIR / RUBRIC_FILES[task]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("task") != task:
        raise ValueError(f"{path}: rubric task mismatch")
    return data


def score_code(task: str, code: str) -> Dict[str, Any]:
    rubric = rubric_for(task)
    results = []
    score = 0
    for criterion in rubric["criteria"]:
        pattern = criterion["pattern"]
        matched = re.search(pattern, code, re.DOTALL) is not None
        satisfied = matched if criterion["kind"] == "present" else not matched
        if satisfied:
            score += 1
        results.append(
            {
                "id": criterion["id"],
                "description": criterion["description"],
                "satisfied": satisfied,
            }
        )
    return {
        "task": task,
        "node": rubric["node"],
        "score": score,
        "max_score": len(rubric["criteria"]),
        "criteria": results,
    }


def cmd_prompt(args: argparse.Namespace) -> int:
    print(prompt_for(args.task, args.arm), end="")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    runner = os.environ.get("ENCYCLOPEDIA_RUNNER")
    if not runner:
        print(
            "error: ENCYCLOPEDIA_RUNNER is not set; export a command that "
            "reads the prompt on stdin and writes the completion to stdout",
            file=sys.stderr,
        )
        return 1
    prompt = prompt_for(args.task, args.arm)
    proc = subprocess.run(
        shlex.split(runner),
        input=prompt,
        text=True,
        capture_output=True,
        timeout=args.timeout,
    )
    if proc.returncode != 0:
        print(
            f"error: provider exited {proc.returncode}: {proc.stderr[-500:]}",
            file=sys.stderr,
        )
        return 1
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(proc.stdout, encoding="utf-8")

    fixtures = Path(args.fixtures)
    fixtures.mkdir(parents=True, exist_ok=True)
    manifest_path = fixtures / "manifest.jsonl"
    entry = {
        "task": args.task,
        "arm": args.arm,
        "output": str(output_path),
        "date": datetime.date.today().isoformat(),
        "runner": runner,
        "pack_hash": None,
    }
    if args.arm == "treatment":
        pack = yaml.safe_load((PACKS_DIR / f"{args.task}.yaml").read_text(encoding="utf-8"))
        entry["pack_hash"] = pack["context_pack_hash"]
    with open(manifest_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    print(
        f"recorded {args.task}/{args.arm} -> {output_path} "
        f"(runner={runner!r}, date={entry['date']})"
    )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    code = Path(args.code_file).read_text(encoding="utf-8")
    result = score_code(args.task, code)
    print(yaml.safe_dump(result, sort_keys=True, allow_unicode=True), end="")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    fixtures = Path(args.fixtures_dir)
    manifest_path = fixtures / "manifest.jsonl"
    rows = []
    if manifest_path.is_file():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        print(
            f"No recorded completions found in {fixtures} (no manifest.jsonl). "
            "Run `runner.py run` first.",
            file=sys.stderr,
        )
        _write_results(args.out, None)
        return 0

    per_task: Dict[str, Dict[str, List[int]]] = {}
    for task in RUBRIC_FILES:
        per_task[task] = {"control": [], "treatment": []}
    for row in rows:
        code = Path(row["output"]).read_text(encoding="utf-8")
        result = score_code(row["task"], code)
        per_task[row["task"]][row["arm"]].append(result["score"])
    _write_results(args.out, per_task)
    return 0


def _mean(values: List[int]) -> Optional[float]:
    return round(sum(values) / len(values), 2) if values else None


def _write_results(out, per_task: Optional[Dict[str, Dict[str, List[int]]]]) -> None:
    out = Path(out)
    lines = [
        "# Experiment results",
        "",
        "Three tasks from the founding brief, Section 8. Five runs per arm, ten",
        "per task, thirty in total. Rubrics are fixed and deterministic",
        "(`experiments/rubrics/`); the score is the count of satisfied criteria.",
        "",
    ]
    if per_task is None:
        lines += [
            "Status: **harness shipped, no completions recorded yet.**",
            "",
            "Reason: the 30 completions are run by the owner against their own",
            "provider via `ENCYCLOPEDIA_RUNNER`; this repository does not execute",
            "an external model. No synthetic fixtures exist and none may be added:",
            "recorded fixtures are only genuine outputs of an identified external",
            "agent run, with model and date noted (Section 8).",
            "",
        ]
    else:
        lines.append("Status: completions recorded; scores below are current as of the manifest.\n")
    lines += [
        "| Task | Node under test | Control mean | Treatment mean | Delta |",
        "|---|---|---|---|---|",
    ]
    for task, node in (
        ("e1", "reliability.idempotency"),
        ("e2", "python.processes.subprocess-safety"),
        ("e3", "python.files.atomic-replacement"),
    ):
        if per_task is None:
            lines.append(f"| {task} | {node} | _ | _ | _ |")
            continue
        control = _mean(per_task[task]["control"])
        treatment = _mean(per_task[task]["treatment"])
        delta = (
            round(treatment - control, 2)
            if control is not None and treatment is not None
            else None
        )
        fmt = lambda v: ("_" if v is None else f"{v:.2f}")
        lines.append(
            f"| {task} | {node} | {fmt(control)} | {fmt(treatment)} | {fmt(delta)} |"
        )
    lines += [
        "",
        "How results are produced: `runner.py run` records each completion and a",
        "manifest entry; `runner.py summarize <fixtures-dir> --out experiments/RESULTS.md`",
        "regenerates this table from the manifest. Treatment-arm reports can be",
        "verified with `encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="Provider-agnostic harness for the engineering-encyclopedia experiments.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prompt", help="print the prompt for a run")
    p.add_argument("task", choices=RUBRIC_FILES)
    p.add_argument("arm", choices=ARMS)

    p = sub.add_parser("run", help="run one completion via $ENCYCLOPEDIA_RUNNER")
    p.add_argument("task", choices=RUBRIC_FILES)
    p.add_argument("arm", choices=ARMS)
    p.add_argument("output", help="file to write the completion to")
    p.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    p.add_argument("--timeout", type=int, default=600)

    p = sub.add_parser("score", help="score recorded code with a rubric")
    p.add_argument("task", choices=RUBRIC_FILES)
    p.add_argument("code_file")

    p = sub.add_parser("summarize", help="regenerate the results table")
    p.add_argument("fixtures_dir", nargs="?", default=str(DEFAULT_FIXTURES))
    p.add_argument("--out", default=str(ROOT / "experiments" / "RESULTS.md"))

    args = parser.parse_args(argv)
    commands = {
        "prompt": cmd_prompt,
        "run": cmd_run,
        "score": cmd_score,
        "summarize": cmd_summarize,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
