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
PACKS_PLACEBO_DIR = ROOT / "experiments" / "packs-placebo"
DEFAULT_FIXTURES = ROOT / "experiments" / "fixtures"

RUBRIC_FILES = {
    "e1": "e1_idempotency.yaml",
    "e2": "e2_subprocess_safety.yaml",
    "e3": "e3_atomic_replacement.yaml",
    "e4": "e4_circuit_breaker.yaml",
    "e5": "e5_correlation_id.yaml",
}

ARMS = ("control", "treatment", "placebo")

# The explicit artifact/report boundary used in the treatment prompts.
# Everything above this line is the artifact to be scored; everything below
# is the Application Report.
ARTIFACT_DELIMITER = "---APPLICATION_REPORT---"

# Report-boundary markers, in detection order. The delimiter is the primary
# boundary; the YAML keys are fallbacks for models that ignore it — every
# report written per the instruction contains one of them (the observed
# miss was a report that started directly at ``knowledge_revision:`` without
# the ``application_report:`` container). These strings cannot occur in code
# artifacts for these tasks.
_REPORT_MARKER_RE = re.compile(
    r"(?m)^\s*("
    r"---APPLICATION_REPORT---"
    r"|application_report:"
    r"|knowledge_revision:"
    r"|context_pack_hash:"
    r")"
)


def extract_artifact(text: str) -> str:
    """The artifact to be scored: the completion with the report removed.

    Cuts at the first report-boundary marker (the ``---APPLICATION_REPORT---``
    delimiter, else ``application_report:`` / ``knowledge_revision:`` /
    ``context_pack_hash:`` — the report's mandatory YAML keys). Control runs
    have no report, so their whole completion is the artifact.

    Rationale: the Application Report reproduces a node's questions verbatim,
    and those strings are exactly what the rubric's absent-patterns look for
    (e.g. a report answering "Is shell=True present anywhere?" contains the
    string ``shell=True``). Scoring the artifact together with its own
    description contaminates the score — see knowledge node
    ``testing.evaluation-contamination``.

    Residual limit (documented, cannot be removed by detection): a model that
    emits a report containing none of the markers cannot have its report
    separated — chat completions return a single free-form string, so no
    protocol can force the delimiter. ``verify-report`` is the final check.
    """
    match = _REPORT_MARKER_RE.search(text)
    if match is not None:
        return text[: match.start()]
    return text


def strip_comments(code: str) -> str:
    """Remove Python ``#`` comments without touching string literals.

    Walks the text tracking string state (single, double and triple quotes)
    and escape sequences; a ``#`` outside a string starts a comment that runs
    to end of line (the newline is preserved so line structure is unchanged).

    Rationale: the rubric's absent-patterns are tripped by prose the model
    wrote as comments (observed: ``# Run the command without shell=True to
    prevent injection`` in an otherwise safe artifact). Comments are not part
    of the executed program, so they are removed before scoring.
    """
    out = []
    i = 0
    n = len(code)
    state = None  # None | "'" | '"' | "'''" | '"""'
    while i < n:
        ch = code[i]
        if state is None:
            if ch in "'\"":
                triple = code[i : i + 3]
                if triple in ("'''", '"""'):
                    state = triple
                    out.append(triple)
                    i += 3
                else:
                    state = ch
                    out.append(ch)
                    i += 1
            elif ch == "#":
                while i < n and code[i] != "\n":
                    i += 1
            else:
                out.append(ch)
                i += 1
        else:
            if ch == "\\":
                out.append(code[i : i + 2])
                i += 2
            elif len(state) == 3 and code[i : i + 3] == state:
                out.append(state)
                i += 3
                state = None
            elif len(state) == 1 and ch == state:
                out.append(ch)
                i += 1
                state = None
            else:
                out.append(ch)
                i += 1
    return "".join(out)


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
    artifact = strip_comments(extract_artifact(code))
    results = []
    score = 0
    for criterion in rubric["criteria"]:
        pattern = criterion["pattern"]
        matched = re.search(pattern, artifact, re.DOTALL) is not None
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
    if args.arm in ("treatment", "placebo"):
        pack_dir = PACKS_DIR if args.arm == "treatment" else PACKS_PLACEBO_DIR
        pack = yaml.safe_load((pack_dir / f"{args.task}.yaml").read_text(encoding="utf-8"))
        entry["pack_hash"] = pack.get("context_pack_hash") if isinstance(pack, dict) else None
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
        for lineno, line in enumerate(
            manifest_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"manifest {manifest_path}:{lineno}: invalid JSON, skipping",
                    file=sys.stderr,
                )
                continue
            # the manifest is self-written but may be tampered or merge-
            # damaged; treat every field as untrusted
            if (
                not isinstance(row, dict)
                or row.get("task") not in RUBRIC_FILES
                or row.get("arm") not in ARMS
                or not isinstance(row.get("output"), str)
            ):
                print(
                    f"manifest {manifest_path}:{lineno}: malformed entry, skipping",
                    file=sys.stderr,
                )
                continue
            out = Path(row["output"])
            if not out.is_file():  # regular file only: no FIFOs/devices/hangs
                print(
                    f"manifest {manifest_path}:{lineno}: output not a regular "
                    f"file, skipping: {out}",
                    file=sys.stderr,
                )
                continue
            rows.append(row)
    if not rows:
        print(
            f"No usable recorded completions found in {fixtures} "
            "(no valid manifest entries). Run `runner.py run` first.",
            file=sys.stderr,
        )
        _write_results(args.out, None)
        return 0

    per_task: Dict[str, Dict[str, List[int]]] = {}
    for task in RUBRIC_FILES:
        per_task[task] = {arm: [] for arm in ARMS}
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
        "| Task | Node under test | Control mean | Treatment mean | Placebo mean | Treatment-Control | Placebo-Control |",
        "|---|---|---|---|---|---|---|",
    ]
    for task, node in (
        ("e1", "reliability.idempotency"),
        ("e2", "python.processes.subprocess-safety"),
        ("e3", "python.files.atomic-replacement"),
    ):
        if per_task is None:
            lines.append(f"| {task} | {node} | _ | _ | _ | _ | _ |")
            continue
        control = _mean(per_task[task]["control"])
        treatment = _mean(per_task[task]["treatment"])
        placebo = _mean(per_task[task].get("placebo", []))
        delta_t = (
            round(treatment - control, 2)
            if control is not None and treatment is not None
            else None
        )
        delta_p = (
            round(placebo - control, 2)
            if control is not None and placebo is not None
            else None
        )
        fmt = lambda v: ("_" if v is None else f"{v:.2f}")
        lines.append(
            f"| {task} | {node} | {fmt(control)} | {fmt(treatment)} | {fmt(placebo)} "
            f"| {fmt(delta_t)} | {fmt(delta_p)} |"
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
