"""Validation of nodes, taxonomy and the Section 3 hard limits.

The validator is the single place that enforces the schema rules and the
hard numeric limits. Tests additionally assert the corpus is exactly the
current node set (see ``tests/test_nodes.py``); the validator itself checks
quality, not quantity.
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List, Tuple

from .loader import Node, corpus_revision, load_nodes, load_taxonomy
from .words import count_words

STATUSES = {"draft", "reviewed", "established", "disputed", "deprecated"}
ORIGINS = {"curated", "documentation", "standard", "research"}

REQUIRED_FIELDS = [
    "id",
    "version",
    "title",
    "kind",
    "status",
    "summary",
    "intent_signals",
    "applies_when",
    "does_not_imply",
    "questions",
    "risks",
    "provenance",
    "keywords",
]

# field -> (min_entries, max_entries); bounds are inclusive.
LIST_LIMITS: Dict[str, Tuple[int, int]] = {
    "intent_signals": (4, 12),
    "questions": (3, 6),
    "does_not_imply": (2, 6),
    "techniques": (0, 8),
    "risks": (0, 8),
}

SUMMARY_MAX_WORDS = 70
MAX_LIST_ENTRY_WORDS = 25
MAX_NODE_WORDS = 500

# Every list-valued field whose entries must stay <= MAX_LIST_ENTRY_WORDS.
# The tests import this exact set so the validator and the suite can never
# drift apart on what "valid" means.
ENTRY_WORD_CHECKED_FIELDS = (
    "intent_signals",
    "applies_when",
    "does_not_apply_when",
    "does_not_imply",
    "questions",
    "techniques",
    "risks",
    "tradeoffs",
    "keywords",
)

ID_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9-]+)+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RELATION_KEYS = ("related", "requires_consideration_of")
CONTEXT_SECTION_KEYS = ("languages", "project_types", "lifecycle_stages")
PROVENANCE_KEYS = ("origin", "created_at", "last_verified_at", "verification_interval_days")


def _err(node: Node, message: str) -> str:
    return f"{node.id}: {message}"


def validate_node(node: Node, ids: set, taxonomy: Dict[str, Any]) -> List[str]:
    """Return a list of validation errors for one node."""
    errors: List[str] = []
    data = node.data

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(_err(node, f"missing required field '{field}'"))

    if not ID_RE.match(node.id):
        errors.append(_err(node, f"id '{node.id}' is not dot-namespaced lowercase"))

    if not isinstance(node.version, int):
        errors.append(_err(node, "version must be an integer"))

    if node.kind not in taxonomy["node-kinds"]:
        errors.append(_err(node, f"kind '{node.kind}' not in taxonomy node-kinds"))

    if node.status not in STATUSES:
        errors.append(_err(node, f"status '{node.status}' not in {{{', '.join(sorted(STATUSES))}}}"))

    # --- word-count and list limits -------------------------------------
    summary = data.get("summary")
    if isinstance(summary, str) and count_words(summary) > SUMMARY_MAX_WORDS:
        errors.append(
            _err(node, f"summary has {count_words(summary)} words, max {SUMMARY_MAX_WORDS}")
        )

    for field, (lo, hi) in LIST_LIMITS.items():
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, list):
            errors.append(_err(node, f"'{field}' must be a list"))
            continue
        if not (lo <= len(value) <= hi):
            errors.append(_err(node, f"'{field}' has {len(value)} entries, need {lo}-{hi}"))

    # Entry-level word limit over the shared field set (Section 3: any
    # single list entry <= 25 words). Tradeoff entries are mappings and are
    # counted across all their sub-values.
    for field in ENTRY_WORD_CHECKED_FIELDS:
        for entry in data.get(field, []) or []:
            if field in LIST_LIMITS and not isinstance(entry, str):
                errors.append(_err(node, f"'{field}' entries must be strings"))
                continue
            if isinstance(entry, (str, dict)):
                words = count_words(entry)
                if words > MAX_LIST_ENTRY_WORDS:
                    errors.append(
                        _err(
                            node,
                            f"'{field}' entry exceeds {MAX_LIST_ENTRY_WORDS} words: {entry!r}",
                        )
                    )
            else:
                errors.append(_err(node, f"'{field}' entries must be strings or mappings"))

    # --- provenance ------------------------------------------------------
    prov = data.get("provenance")
    if not isinstance(prov, dict):
        errors.append(_err(node, "provenance must be a mapping"))
    else:
        for key in PROVENANCE_KEYS:
            if key not in prov:
                errors.append(_err(node, f"provenance missing '{key}'"))
        origin = prov.get("origin")
        if origin not in ORIGINS:
            errors.append(_err(node, f"provenance.origin '{origin}' not in {{{', '.join(sorted(ORIGINS))}}}"))
        if origin == "curated" and not str(prov.get("rationale", "")).strip():
            errors.append(_err(node, "curated provenance requires a non-empty rationale"))
        for key in ("created_at", "last_verified_at"):
            value = prov.get(key)
            # PyYAML parses YYYY-MM-DD scalars as datetime.date; accept both.
            valid_date = isinstance(value, datetime.date) or (
                isinstance(value, str) and DATE_RE.match(value)
            )
            if not valid_date:
                errors.append(_err(node, f"provenance.{key} must be a YYYY-MM-DD date"))
        interval = prov.get("verification_interval_days")
        if not isinstance(interval, int) or interval <= 0:
            errors.append(_err(node, "verification_interval_days must be a positive integer"))

    # --- relations -------------------------------------------------------
    relations = data.get("relations") or {}
    if not isinstance(relations, dict):
        errors.append(_err(node, "relations must be a mapping"))
    else:
        for key in RELATION_KEYS:
            for target in relations.get(key, []) or []:
                if target not in ids:
                    errors.append(_err(node, f"relation target '{target}' does not exist in the corpus"))
                if key not in taxonomy["relation-types"]:
                    errors.append(_err(node, f"relation type '{key}' not in taxonomy relation-types"))

    # --- contexts --------------------------------------------------------
    contexts = data.get("contexts") or {}
    if not isinstance(contexts, dict):
        errors.append(_err(node, "contexts must be a mapping"))
    else:
        known = taxonomy["contexts"]
        for section in CONTEXT_SECTION_KEYS:
            for value in contexts.get(section, []) or []:
                if value not in known[section]:
                    errors.append(_err(node, f"contexts.{section} value '{value}' not in taxonomy"))

    # --- keywords --------------------------------------------------------
    keywords = data.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        errors.append(_err(node, "keywords must be a non-empty list"))
    elif not all(isinstance(k, str) for k in keywords):
        errors.append(_err(node, "keywords must be strings"))

    # --- whole-file budget ------------------------------------------------
    total = count_words(data)
    if total > MAX_NODE_WORDS:
        errors.append(_err(node, f"whole node file has {total} words, max {MAX_NODE_WORDS}"))

    return errors


def validate_taxonomy(taxonomy: Dict[str, Any]) -> List[str]:
    """Return a list of errors for the taxonomy enumerations themselves."""
    errors: List[str] = []
    for name in ("node-kinds", "contexts", "relation-types"):
        value = taxonomy.get(name)
        if name == "contexts":
            if not isinstance(value, dict) or not all(
                isinstance(v, list) and all(isinstance(x, str) for x in v)
                for v in value.values()
            ):
                errors.append(f"taxonomy '{name}' must be a mapping of string lists")
        else:
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                errors.append(f"taxonomy '{name}' must be a list of strings")
    return errors


def validate_all() -> Tuple[bool, List[str], List[Node]]:
    """Validate the whole corpus and taxonomy.

    Returns ``(ok, errors, nodes)``. ``errors`` is empty when ``ok`` is True.
    """
    errors: List[str] = []
    nodes = load_nodes()
    ids = {node.id for node in nodes}
    if len(ids) != len(nodes):
        seen: Dict[str, int] = {}
        for node in nodes:
            seen[node.id] = seen.get(node.id, 0) + 1
        for node_id, count in seen.items():
            if count > 1:
                errors.append(f"duplicate node id: {node_id}")

    taxonomy = load_taxonomy()
    errors.extend(validate_taxonomy(taxonomy))

    for node in nodes:
        errors.extend(validate_node(node, ids, taxonomy))

    return (not errors, errors, nodes)


def corpus_stats() -> str:
    """Short human line summarising a validated corpus."""
    ok, errors, nodes = validate_all()
    if not ok:
        return f"invalid: {len(errors)} error(s)"
    return (
        f"OK: {len(nodes)} nodes validated "
        f"(revision {corpus_revision(nodes)})"
    )
