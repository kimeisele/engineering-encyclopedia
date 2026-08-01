"""Application Report verification (Section 7 — the actual product).

``verify-report`` is deterministic and offline: it requires the original
context pack (``--pack`` is mandatory) and checks that the report is bound to
that pack, bound to the corpus, and bound to the node content. A report alone
cannot reveal a silently dropped node; the pack supplies the missing half of
the evidence.

Exit code 0 on pass, 1 on failure, with a machine-readable failure list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .canonical import canonical_bytes, sha256_prefix
from .loader import Node, load_yaml_file
from .words import count_words

MAX_ANSWER_WORDS = 40


def _load_yaml(path: Path) -> Optional[Any]:
    """Load report/pack YAML with the shared size and complexity guards."""
    return load_yaml_file(path)


def _fail(failures: List[Dict[str, str]], code: str, detail: str) -> None:
    failures.append({"code": code, "detail": detail})


def verify_report(
    report_path: Path,
    pack_path: Path,
    nodes: List[Node],
) -> Tuple[bool, List[Dict[str, str]]]:
    """Verify an Application Report against its context pack.

    Returns ``(ok, failures)`` where ``failures`` is a machine-readable list
    of ``{"code", "detail"}`` dicts. ``ok`` is True iff the list is empty.
    """
    failures: List[Dict[str, str]] = []
    node_by_id = {node.id: node for node in nodes}

    try:
        report = _load_yaml(report_path)
        pack = _load_yaml(pack_path)
    except (OSError, ValueError) as exc:
        return False, [{"code": "unreadable", "detail": str(exc)}]
    except (yaml.YAMLError, RecursionError) as exc:
        return False, [{"code": "invalid_yaml", "detail": str(exc)}]

    if not isinstance(report, dict) or not isinstance(report.get("application_report"), dict):
        _fail(failures, "missing_application_report", "report has no application_report mapping")
        return False, failures
    app = report["application_report"]

    if not isinstance(pack, dict):
        _fail(failures, "invalid_pack", "pack file is not a mapping")
        return False, failures

    # --- binding to the pack --------------------------------------------
    if app.get("context_pack_hash") != pack.get("context_pack_hash"):
        _fail(
            failures,
            "context_pack_hash_mismatch",
            "report context_pack_hash does not match the supplied pack",
        )
    computed = sha256_prefix(
        canonical_bytes(
            {k: v for k, v in pack.items() if k != "context_pack_hash"}
        )
    )
    if pack.get("context_pack_hash") != computed:
        _fail(
            failures,
            "pack_hash_mismatch",
            f"supplied pack hash {pack.get('context_pack_hash')!r} does not match "
            f"its content ({computed!r})",
        )

    if app.get("knowledge_revision") != pack.get("knowledge_revision"):
        _fail(
            failures,
            "knowledge_revision_mismatch",
            "report knowledge_revision differs from the pack",
        )

    context_pack = pack.get("context_pack")
    if not isinstance(context_pack, dict):
        _fail(failures, "invalid_pack", "pack has no context_pack mapping")
        return False, failures
    pack_node_ids = []
    for section in ("primary", "supporting"):
        for entry in context_pack.get(section, []) or []:
            if isinstance(entry, dict) and "id" in entry:
                pack_node_ids.append(entry["id"])
    pack_node_set = set(pack_node_ids)

    applied = app.get("applied", []) or []
    not_applied = app.get("not_applied", []) or []
    if not isinstance(applied, list) or not isinstance(not_applied, list):
        _fail(failures, "invalid_report", "applied and not_applied must be lists")
        return False, failures

    def _node_id(entry: Any) -> Optional[str]:
        return entry.get("node") if isinstance(entry, dict) else None

    # --- coverage: each pack node exactly once across both dispositions ---
    dispositions: Dict[str, List[str]] = {}
    for disposition, entries in (("applied", applied), ("not_applied", not_applied)):
        for entry in entries:
            node_id = _node_id(entry)
            if node_id is None:
                _fail(failures, "invalid_entry", f"{disposition} entry lacks 'node'")
                continue
            dispositions.setdefault(node_id, []).append(disposition)
            if node_id not in pack_node_set:
                _fail(
                    failures,
                    "node_not_in_pack",
                    f"{node_id} appears in the report but not in the pack",
                )
    for node_id, count in dispositions.items():
        if len(count) > 1:
            _fail(
                failures,
                "duplicate_disposition",
                f"{node_id} listed {len(count)} times: {', '.join(sorted(set(count)))}",
            )
    missing = pack_node_set - set(dispositions)
    for node_id in sorted(missing):
        _fail(
            failures,
            "omitted_pack_node",
            f"{node_id} is in the pack but neither applied nor not_applied",
        )

    # --- binding to the corpus -------------------------------------------
    for disposition, entries in (("applied", applied), ("not_applied", not_applied)):
        for entry in entries:
            node_id = _node_id(entry)
            if node_id is None:
                continue
            corpus_node = node_by_id.get(node_id)
            if corpus_node is None:
                _fail(failures, "unknown_node", f"{node_id} does not exist in the corpus")
                continue
            if disposition == "applied":
                if entry.get("version") != corpus_node.version:
                    _fail(
                        failures,
                        "wrong_version",
                        f"{node_id}: version {entry.get('version')} != corpus {corpus_node.version}",
                    )
                if entry.get("hash") != corpus_node.content_hash:
                    _fail(
                        failures,
                        "wrong_hash",
                        f"{node_id}: hash {entry.get('hash')} != corpus {corpus_node.content_hash}",
                    )

    # --- binding to the node content -------------------------------------
    corpus_questions: Dict[str, List[str]] = {
        node.id: [str(q) for q in (node.data.get("questions", []) or [])]
        for node in nodes
    }
    for entry in applied:
        node_id = _node_id(entry)
        if node_id is None or node_id not in corpus_questions:
            continue
        for question in entry.get("questions_answered", []) or []:
            q = question.get("question") if isinstance(question, dict) else None
            if q is not None and q not in corpus_questions[node_id]:
                _fail(
                    failures,
                    "altered_question",
                    f"{node_id}: question {q!r} is not a question of this node",
                )
            answer = question.get("answer") if isinstance(question, dict) else None
            location = question.get("location") if isinstance(question, dict) else None
            if not (isinstance(answer, str) and answer.strip()):
                _fail(failures, "empty_answer", f"{node_id}: answer must be non-empty")
            elif count_words(str(answer)) > MAX_ANSWER_WORDS:
                _fail(
                    failures,
                    "answer_too_long",
                    f"{node_id}: answer exceeds {MAX_ANSWER_WORDS} words",
                )
            if not (isinstance(location, str) and location.strip()):
                _fail(failures, "empty_location", f"{node_id}: location must be non-empty")

        # every question of an applied node must be answered or marked unanswered
        answered = {
            (q.get("question") if isinstance(q, dict) else None)
            for q in entry.get("questions_answered", []) or []
        }
        unanswered = {
            (q.get("question") if isinstance(q, dict) else None)
            for q in entry.get("unanswered", []) or []
        }
        # a question cannot be both answered and unanswered — that is a
        # flat contradiction in the evidence
        for question in sorted(answered & unanswered):
            if question is not None:
                _fail(
                    failures,
                    "contradictory_disposition",
                    f"{node_id}: question {question!r} is both answered and unanswered",
                )
        # and no question may be repeated within one list
        for label, items in (
            ("questions_answered", entry.get("questions_answered", []) or []),
            ("unanswered", entry.get("unanswered", []) or []),
        ):
            seen = set()
            for item in items:
                q = item.get("question") if isinstance(item, dict) else None
                if q is not None:
                    if q in seen:
                        _fail(
                            failures,
                            "duplicate_question",
                            f"{node_id}: question {q!r} repeated in {label}",
                        )
                    seen.add(q)
        for question in corpus_questions[node_id]:
            if question not in answered and question not in unanswered:
                _fail(
                    failures,
                    "omitted_question",
                    f"{node_id}: question {question!r} is neither answered nor unanswered",
                )
        for entry_un in entry.get("unanswered", []) or []:
            q = entry_un.get("question") if isinstance(entry_un, dict) else None
            if q is not None and q not in corpus_questions[node_id]:
                _fail(
                    failures,
                    "altered_question",
                    f"{node_id}: unanswered question {q!r} is not a question of this node",
                )

    for entry in not_applied:
        reason = entry.get("reason") if isinstance(entry, dict) else None
        if not (isinstance(reason, str) and reason.strip()):
            _fail(failures, "empty_reason", "not_applied entry lacks a non-empty reason")

    return (not failures, failures)
