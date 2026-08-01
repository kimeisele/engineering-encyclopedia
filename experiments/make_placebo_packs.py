#!/usr/bin/env python3
"""Build placebo packs and placebo prompts for the Section 8 experiment.

A placebo pack has the same length and structure as the treatment pack for a
task (same number of node slots, same guidance fields, same number of
questions) but its content comes from a node irrelevant to the task —
observability.error-context. If placebo ≈ treatment, the pack effect is
structural (longer, more structured prompt), not knowledge.

The treatment pack structure is mirrored so the placebo prompt differs from
the treatment prompt only in the pack's content. The pack hash is computed
with the same canonical serialisation as the corpus (sorted keys, block
style, no anchors), so `encyclopedia verify-report` can verify placebo
reports against these packs. This script imports nothing from src/.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKS_DIR = ROOT / "experiments" / "packs"
PACKS_PLACEBO_DIR = ROOT / "experiments" / "packs-placebo"
TASKS_DIR = ROOT / "experiments" / "tasks"
KNOWLEDGE = ROOT / "knowledge" / "observability" / "error-context.yaml"

TASKS = {
    "e1": "Write a worker that consumes jobs from a queue and charges a customer.",
    "e2": "Write a Python function that runs a git command with a user-supplied branch name.",
    "e3": "Write a function that updates a JSON config file on disk.",
    "e4": "Write a function that calls a downstream HTTP API and must not hammer it while it is down.",
    "e5": "Write an error handler for a two-service request so an operator can trace one request across both services.",
}

IRRELEVANT_NODE = "observability.error-context"

GUIDANCE_FIELDS = ("summary", "questions", "does_not_imply", "risks")
RELEVANCE = "unrelated to this task - structural control"


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def canonical_bytes(data: Any) -> bytes:
    return yaml.dump(
        data,
        Dumper=_NoAliasDumper,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    ).encode("utf-8")


def sha256_prefix(data: bytes, length: int = 12) -> str:
    return hashlib.sha256(data).hexdigest()[:length]


def build_placebo_pack(task: str, node: Dict[str, Any]) -> Dict[str, Any]:
    """Mirror the treatment pack's slot count, filled with *node* content."""
    treatment = yaml.safe_load((PACKS_DIR / f"{task}.yaml").read_text(encoding="utf-8"))
    slots = len(treatment["context_pack"]["primary"]) + len(
        treatment["context_pack"]["supporting"]
    )
    section_size = len(treatment["context_pack"]["primary"])

    entry = {
        "id": node["id"],
        "version": node["version"],
        "hash": sha256_prefix(canonical_bytes(node)),
        "relevance": RELEVANCE,
    }
    for field in GUIDANCE_FIELDS:
        entry[field] = node[field]

    primary = [dict(entry) for _ in range(section_size)]
    supporting = [dict(entry) for _ in range(slots - section_size)]

    pack = {
        "request": {"original": TASKS[task]},
        "knowledge_revision": sha256_prefix(
            b"".join(sha256_prefix(canonical_bytes(node)).encode("ascii") for _ in range(slots))
        ),
        "context_pack_hash": "",
        "retrieval_backend": "placebo",
        "context_pack": {"primary": primary, "supporting": supporting},
        "trace": {
            "selected": [IRRELEVANT_NODE] * slots,
            "excluded": [],
            "truncated": False,
        },
    }
    pack["context_pack_hash"] = sha256_prefix(
        canonical_bytes({k: v for k, v in pack.items() if k != "context_pack_hash"})
    )
    return pack


def build_placebo_prompt(task: str, pack: Dict[str, Any]) -> str:
    treatment = (TASKS_DIR / f"{task}-treatment.txt").read_text(encoding="utf-8")
    intro_marker = "You receive the following context pack of engineering knowledge."
    report_marker = "\nAPPLICATION REPORT"
    head = treatment.split(intro_marker, 1)[0] + intro_marker + "\n\n"
    tail = treatment.split(report_marker, 1)[1]
    return (
        head
        + _dump(pack)
        + "\n"
        + report_marker
        + tail
    )


def _dump(data: Any) -> str:
    """No-alias YAML: identical slots must not collapse to anchors/aliases,
    or the placebo prompt would be shorter than the treatment prompt."""
    return yaml.dump(
        data,
        Dumper=_NoAliasDumper,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )


def main() -> int:
    node = yaml.safe_load(KNOWLEDGE.read_text(encoding="utf-8"))
    assert node["id"] == IRRELEVANT_NODE
    PACKS_PLACEBO_DIR.mkdir(parents=True, exist_ok=True)
    for task in TASKS:
        pack = build_placebo_pack(task, node)
        pack_path = PACKS_PLACEBO_DIR / f"{task}.yaml"
        pack_path.write_text(_dump(pack), encoding="utf-8")
        prompt = build_placebo_prompt(task, pack)
        (TASKS_DIR / f"{task}-placebo.txt").write_text(prompt, encoding="utf-8")
        words = len(_dump(pack).split())
        treatment_words = len(
            (PACKS_DIR / f"{task}.yaml").read_text(encoding="utf-8").split()
        )
        print(
            f"{task}: placebo pack {words} words vs treatment {treatment_words} "
            f"words, hash {pack['context_pack_hash']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
