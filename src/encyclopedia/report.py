"""Application Report verification (Section 7 — optional audit path).

``verify-report`` is deterministic and offline: it requires the original
context pack (``--pack`` is mandatory) and checks that the report is bound
to that pack. It proves **completeness and binding** — the report is the
pack's, every pack node is disposed exactly once, every question of an
applied node is answered or marked unanswered, answers carry a non-empty
location. It does **not** prove that the claims about the code are true:
verification is syntactic and offline, and the pack is the primary truth
(Slice 2), not the current corpus.

An optional ``--root`` mode adds purely mechanical location checks
(format ``path:41`` / ``path:41-48``, file inside root, file exists, line
range exists, no path traversal) — still nothing semantic, no LLM, no AST.

Exit code 0 on pass, 1 on failure, with a machine-readable failure list.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .canonical import canonical_bytes, sha256_prefix
from .loader import Node, corpus_revision, load_yaml_file
from .words import count_words

MAX_ANSWER_WORDS = 40

# location format: ``path:41`` or ``path:41-48`` — a relative path (no
# leading slash, no ``..`` segment) followed by a positive line range.
_LOCATION_RE = re.compile(r"^(?P<path>.+?):(?P<start>\d+)(?:-(?P<end>\d+))?$")


def _load_yaml(path: Path) -> Optional[Any]:
    """Load report/pack YAML with the shared size and complexity guards."""
    return load_yaml_file(path)


def _fail(failures: List[Dict[str, str]], code: str, detail: str) -> None:
    failures.append({"code": code, "detail": detail})


def _verify_mechanical_locations(
    app: Dict[str, Any], root: Path, failures: List[Dict[str, str]]
) -> None:
    """Mechanical ``--root`` location checks (Slice 3).

    Checks only the location syntax of every answered question: format
    ``path:41`` / ``path:41-48``, no path traversal, the file is inside
    *root*, exists, and the line range exists in it. Nothing semantic —
    this never reads whether the answer is actually true.
    """
    try:
        root_resolved = root.resolve()
    except OSError as exc:
        _fail(failures, "root_unreadable", f"cannot resolve --root {root}: {exc}")
        return
    for entry in app.get("applied", []) or []:
        if not isinstance(entry, dict):
            continue
        node_id = entry.get("node", "?")
        for question in entry.get("questions_answered", []) or []:
            if not isinstance(question, dict):
                continue
            location = question.get("location")
            if not isinstance(location, str) or not location.strip():
                continue  # empty_location is already a pack-bound failure
            match = _LOCATION_RE.match(location.strip())
            if match is None:
                _fail(
                    failures,
                    "location_format",
                    f"{node_id}: location {location!r} is not 'path:41' or 'path:41-48'",
                )
                continue
            rel = match.group("path")
            start = int(match.group("start"))
            end = int(match.group("end")) if match.group("end") else start
            if start < 1 or end < start:
                _fail(
                    failures,
                    "location_format",
                    f"{node_id}: location {location!r} has an invalid line range",
                )
                continue
            rel_path = Path(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                _fail(
                    failures,
                    "location_traversal",
                    f"{node_id}: location {location!r} escapes --root",
                )
                continue
            candidate = root_resolved / rel_path
            try:
                candidate_resolved = candidate.resolve()
            except OSError as exc:
                _fail(
                    failures,
                    "location_traversal",
                    f"{node_id}: cannot resolve {location!r}: {exc}",
                )
                continue
            try:
                candidate_resolved.relative_to(root_resolved)
            except ValueError:
                _fail(
                    failures,
                    "location_outside_root",
                    f"{node_id}: location {location!r} resolves outside --root",
                )
                continue
            if not candidate_resolved.is_file():
                _fail(
                    failures,
                    "location_file_missing",
                    f"{node_id}: file {rel!r} does not exist under --root",
                )
                continue
            try:
                with open(candidate_resolved, "r", encoding="utf-8") as handle:
                    line_count = sum(1 for _ in itertools.islice(handle, end))
            except OSError as exc:
                _fail(
                    failures,
                    "location_unreadable",
                    f"{node_id}: cannot read {rel!r}: {exc}",
                )
                continue
            if line_count < end:
                _fail(
                    failures,
                    "location_line_out_of_range",
                    f"{node_id}: {rel!r} has {line_count} lines, location ends at {end}",
                )


def verify_report(
    report_path: Path,
    pack_path: Path,
    nodes: List[Node],
    root: Optional[Path] = None,
) -> Tuple[bool, List[Dict[str, str]], Dict[str, Any]]:
    """Verify an Application Report against its context pack.

    Proves **completeness and binding** only: the report is bound to the
    supplied pack, every pack node is disposed exactly once, every question
    of an applied node is answered or marked unanswered, answers are
    non-empty and ≤ 40 words, locations are non-empty. It does **not** prove
    that the claims about the code are true — verification is syntactic and
    offline. With *root* set, purely mechanical location checks run on every
    answered location (see ``_verify_mechanical_locations``).

    Primary truth is the **supplied pack** (Slice 2): pack hash and
    ``knowledge_revision`` binding, node presence, versions and hashes as
    recorded in the pack, questions as bound by the pack's node hashes, and
    every pack node disposed exactly once. Verification is stable against
    corpus growth: a historical pack stays verifiable after the corpus moves
    on, so past reports are never retroactively invalidated by a node edit.

    Returns ``(ok, failures, corpus)``:
    - ``ok``/``failures`` cover the pack-bound checks above (plus the
      mechanical ``--root`` location checks when *root* is given);
    - ``corpus`` is a **separate, non-fatal** cross-check against the current
      corpus: ``{"status": "current" | "drifted" | "stale" | "unknown",
      "details": [...]}``. It runs fully only when the report's
      ``knowledge_revision`` equals the current corpus revision; otherwise
      it reports ``stale`` (the corpus has moved on) and never fails the
      report. The report is bound to the pack it was written against, not to
      a corpus that may have changed since.

    Where the pack records no questions (``compact`` detail), question-level
    checks fall back to the corpus questions only while the pack-recorded
    hash still matches the current corpus node; otherwise those checks are
    skipped and noted in ``corpus.details``.
    """
    failures: List[Dict[str, str]] = []
    corpus: Dict[str, Any] = {"status": "unknown", "details": []}
    node_by_id = {node.id: node for node in nodes}
    current_revision = corpus_revision(nodes)

    try:
        report = _load_yaml(report_path)
        pack = _load_yaml(pack_path)
    except (OSError, ValueError) as exc:
        return False, [{"code": "unreadable", "detail": str(exc)}], corpus
    except (yaml.YAMLError, RecursionError) as exc:
        return False, [{"code": "invalid_yaml", "detail": str(exc)}], corpus

    if not isinstance(report, dict) or not isinstance(report.get("application_report"), dict):
        _fail(failures, "missing_application_report", "report has no application_report mapping")
        return False, failures, corpus
    app = report["application_report"]

    if not isinstance(pack, dict):
        _fail(failures, "invalid_pack", "pack file is not a mapping")
        return False, failures, corpus

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
        return False, failures, corpus
    pack_entries: Dict[str, Dict[str, Any]] = {}
    for section in ("primary", "supporting"):
        for entry in context_pack.get(section, []) or []:
            if isinstance(entry, dict) and "id" in entry:
                pack_entries[entry["id"]] = entry
    pack_node_set = set(pack_entries)

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

    # --- applied version/hash against the PACK-recorded values -----------
    # The report echoes what the pack recorded at composition time; the
    # current corpus may have moved on and must not invalidate that.
    for entry in applied:
        node_id = _node_id(entry)
        if node_id is None or node_id not in pack_entries:
            continue
        recorded = pack_entries[node_id]
        if entry.get("version") != recorded.get("version"):
            _fail(
                failures,
                "wrong_version",
                f"{node_id}: version {entry.get('version')} != pack-recorded {recorded.get('version')}",
            )
        if entry.get("hash") != recorded.get("hash"):
            _fail(
                failures,
                "wrong_hash",
                f"{node_id}: hash {entry.get('hash')} != pack-recorded {recorded.get('hash')}",
            )

    # --- questions bound by the pack's node hashes -------------------------
    def questions_for(node_id: str) -> Optional[List[str]]:
        """The authoritative question list for a pack node.

        Pack-recorded questions win where the pack carries them
        (``guidance``/``full``). For a ``compact`` pack (no questions) the
        corpus questions are used only while the pack-recorded hash still
        matches the current corpus node — i.e. the corpus content is what the
        pack recorded. Otherwise the pack binds no question content.
        """
        entry = pack_entries.get(node_id)
        if entry is None:
            return None
        if isinstance(entry.get("questions"), list):
            return [str(q) for q in entry["questions"]]
        corpus_node = node_by_id.get(node_id)
        if corpus_node is not None and entry.get("hash") == corpus_node.content_hash:
            return [str(q) for q in (corpus_node.data.get("questions", []) or [])]
        return None

    for entry in applied:
        node_id = _node_id(entry)
        if node_id is None or node_id not in pack_entries:
            continue
        questions = questions_for(node_id)
        if questions is None:
            corpus["details"].append(
                f"questions not verified for {node_id}: the pack records no "
                "questions and the corpus no longer matches the pack-recorded hash"
            )
        # answers and locations are validated against the report's own
        # content regardless of the authoritative question set
        for question in entry.get("questions_answered", []) or []:
            if not isinstance(question, dict):
                continue
            answer = question.get("answer")
            location = question.get("location")
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
        if questions is None:
            continue
        question_set = set(questions)
        for question in entry.get("questions_answered", []) or []:
            q = question.get("question") if isinstance(question, dict) else None
            if q is not None and q not in question_set:
                _fail(
                    failures,
                    "altered_question",
                    f"{node_id}: question {q!r} is not a question of this node",
                )

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
        for question in questions:
            if question not in answered and question not in unanswered:
                _fail(
                    failures,
                    "omitted_question",
                    f"{node_id}: question {question!r} is neither answered nor unanswered",
                )
        for entry_un in entry.get("unanswered", []) or []:
            q = entry_un.get("question") if isinstance(entry_un, dict) else None
            if q is not None and q not in question_set:
                _fail(
                    failures,
                    "altered_question",
                    f"{node_id}: unanswered question {q!r} is not a question of this node",
                )

    for entry in not_applied:
        reason = entry.get("reason") if isinstance(entry, dict) else None
        if not (isinstance(reason, str) and reason.strip()):
            _fail(failures, "empty_reason", "not_applied entry lacks a non-empty reason")

    # --- current-corpus cross-check (separate, conditional, non-fatal) ----
    report_revision = app.get("knowledge_revision")
    if report_revision == current_revision:
        drifted = []
        for node_id in sorted(pack_entries):
            corpus_node = node_by_id.get(node_id)
            recorded = pack_entries[node_id]
            if corpus_node is None:
                drifted.append(f"{node_id}: missing from corpus")
            elif recorded.get("hash") != corpus_node.content_hash:
                drifted.append(
                    f"{node_id}: corpus hash {corpus_node.content_hash} "
                    f"!= pack-recorded {recorded.get('hash')}"
                )
        corpus = {
            "status": "current" if not drifted else "drifted",
            "details": drifted,
        }
    else:
        corpus = {
            "status": "stale",
            "details": [
                f"corpus revision {current_revision} != report revision "
                f"{report_revision!r}; the corpus has moved on"
            ],
        }

    # --- optional mechanical --root location checks (Slice 3) -------------
    if root is not None:
        _verify_mechanical_locations(app, root, failures)

    return (not failures, failures, corpus)
