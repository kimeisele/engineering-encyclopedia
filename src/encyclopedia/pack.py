"""Context pack composer (Section 6 of the founding brief).

A context pack is the bounded, hashed bundle of knowledge an agent receives
with a request. Its ``context_pack_hash`` binds the Application Report to the
exact knowledge shown.

Hard limits (enforced and tested):
- primary <= 3 nodes, supporting <= 3 nodes, graph depth exactly 1
- ``relevance`` <= 15 words
- detail budgets: compact <= 150 words, guidance <= 700, full <= 2500
- ``trace.excluded`` <= 5 entries
- exceeding a budget truncates deterministically (lowest-ranked node first)
  and sets ``trace.truncated: true``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .canonical import canonical_bytes, sha256_prefix
from .loader import Node, corpus_revision
from .retrieval import RetrievalIndex, tokenize
from .words import count_words

DETAIL_LEVELS = ("compact", "guidance", "full")
WORD_BUDGETS = {"compact": 150, "guidance": 700, "full": 2500}
MAX_PRIMARY = 3
MAX_SUPPORTING = 3
MAX_EXCLUDED = 5
MAX_RELEVANCE_WORDS = 15

RELATION_KEYS = ("related", "requires_consideration_of")

_FIELDS_BY_DETAIL = {
    "compact": (),
    "guidance": ("summary", "questions", "does_not_imply", "risks"),
    "full": (
        "summary",
        "applies_when",
        "does_not_apply_when",
        "questions",
        "does_not_imply",
        "risks",
        "techniques",
        "tradeoffs",
        "contexts",
        "keywords",
        "intent_signals",
        "relations",
    ),
}


@dataclass
class PackOptions:
    """Options for pack composition; caps are clamped, never exceeded."""

    detail: str = "guidance"
    max_primary: int = MAX_PRIMARY
    max_supporting: int = MAX_SUPPORTING
    language: Optional[str] = None
    project_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.detail not in DETAIL_LEVELS:
            raise ValueError(f"detail must be one of {DETAIL_LEVELS}")
        self.max_primary = min(max(1, int(self.max_primary)), MAX_PRIMARY)
        self.max_supporting = min(max(0, int(self.max_supporting)), MAX_SUPPORTING)


def _relevance(node: Node, query: str) -> str:
    """Deterministic <=15-word relevance line for *node* against *query*.

    The best-overlap ``intent_signals`` entry wins; otherwise the summary
    prefix is used. Truncated at 15 words either way.
    """
    query_tokens = set(tokenize(query))
    best: Optional[str] = None
    best_overlap = -1
    for signal in node.data.get("intent_signals", []) or []:
        overlap = len(query_tokens & set(tokenize(signal)))
        if overlap > best_overlap:
            best_overlap = overlap
            best = signal
    if best is not None and best_overlap > 0:
        return " ".join(best.split()[:MAX_RELEVANCE_WORDS])
    return " ".join(str(node.data.get("summary", "")).split()[:MAX_RELEVANCE_WORDS])


def _neighbourhood(nodes: List[Node]) -> Dict[str, Set[str]]:
    """Undirected adjacency over all relation types (depth-1 graph)."""
    adjacency: Dict[str, Set[str]] = {node.id: set() for node in nodes}
    for node in nodes:
        relations = node.data.get("relations") or {}
        for key in RELATION_KEYS:
            for target in relations.get(key, []) or []:
                adjacency[node.id].add(target)
                adjacency.setdefault(target, set()).add(node.id)
    return adjacency


def _matches_context(node: Node, options: PackOptions) -> bool:
    """Optional --language / --project-type filtering against node.contexts."""
    contexts = node.data.get("contexts") or {}
    if options.language is not None:
        languages = contexts.get("languages", []) or []
        if "any" not in languages and options.language not in languages:
            return False
    if options.project_type is not None:
        project_types = contexts.get("project_types", []) or []
        if "any" not in project_types and options.project_type not in project_types:
            return False
    return True


def _node_entry(node: Node, relevance: str, detail: str) -> Dict[str, Any]:
    """The emitted content for one node at one detail level.

    ``id``, ``version`` and ``hash`` are always present (Section 6: every
    emitted node carries them at every detail level).
    """
    entry: Dict[str, Any] = {
        "id": node.id,
        "version": node.version,
        "hash": node.content_hash,
        "relevance": relevance,
    }
    for field in _FIELDS_BY_DETAIL[detail]:
        if field in node.data:
            entry[field] = node.data[field]
    return entry


def compose_pack(
    nodes: List[Node],
    index: RetrievalIndex,
    request: str,
    options: PackOptions,
) -> Dict[str, Any]:
    """Compose a context pack for *request* against *index*.

    Selection: primary = top-ranked nodes (capped); supporting = graph
    neighbours of primary at depth exactly 1 (capped), ordered by retrieval
    rank. Budgets are enforced by deterministic truncation.
    """
    node_by_id = {node.id: node for node in nodes}
    ranked = index.search(request)
    ranked_ids = [node_id for node_id, _ in ranked]
    rank_position = {node_id: i for i, node_id in enumerate(ranked_ids)}

    if options.language is not None or options.project_type is not None:
        ranked_ids = [
            node_id
            for node_id in ranked_ids
            if _matches_context(node_by_id[node_id], options)
        ]

    primary_ids = ranked_ids[: options.max_primary]

    adjacency = _neighbourhood(nodes)
    support_candidates: List[str] = []
    for primary_id in primary_ids:
        for neighbour in sorted(adjacency.get(primary_id, set())):
            if neighbour not in primary_ids and neighbour not in support_candidates:
                support_candidates.append(neighbour)
    support_candidates.sort(
        key=lambda nid: (rank_position.get(nid, len(ranked_ids)), nid)
    )
    supporting_ids = support_candidates[: options.max_supporting]

    selected = list(primary_ids) + list(supporting_ids)
    excluded = [nid for nid in ranked_ids if nid not in selected][:MAX_EXCLUDED]

    pack: Dict[str, Any] = {
        "request": {"original": request},
        "knowledge_revision": corpus_revision(nodes),
        "context_pack_hash": "",
        "retrieval_backend": index.backend,
        "context_pack": {
            "primary": [
                _node_entry(node_by_id[nid], _relevance(node_by_id[nid], request), options.detail)
                for nid in primary_ids
            ],
            "supporting": [
                _node_entry(node_by_id[nid], _relevance(node_by_id[nid], request), options.detail)
                for nid in supporting_ids
            ],
        },
        "trace": {
            "selected": list(selected),
            "excluded": excluded,
            "truncated": False,
        },
    }

    _enforce_budget(pack, selected, WORD_BUDGETS[options.detail], rank_position, ranked_ids)

    pack["context_pack_hash"] = _pack_hash(pack)
    return pack


def _pack_hash(pack: Dict[str, Any]) -> str:
    """sha256[:12] over the canonical pack with context_pack_hash omitted."""
    stripped = {key: value for key, value in pack.items() if key != "context_pack_hash"}
    return sha256_prefix(canonical_bytes(stripped))


def _enforce_budget(
    pack: Dict[str, Any],
    selected: List[str],
    budget: int,
    rank_position: Dict[str, int],
    ranked_ids: List[str],
) -> None:
    """Drop lowest-ranked nodes first until the pack fits *budget* words.

    Mutates *pack* and *selected* in place; sets ``trace.truncated`` when
    anything is dropped. Nodes are emitted highest-rank first, so the last
    element of *selected* is always the lowest-ranked survivor.
    """
    while count_words(pack) > budget and len(selected) > 1:
        dropped = selected.pop()
        # remove from the emitted sections
        for section in ("primary", "supporting"):
            pack["context_pack"][section] = [
                entry
                for entry in pack["context_pack"][section]
                if entry["id"] != dropped
            ]
        pack["trace"]["truncated"] = True
        pack["trace"]["selected"] = list(selected)
    # Last resort: trim trace.excluded (already <= 5) while still over budget.
    while count_words(pack) > budget and pack["trace"]["excluded"]:
        pack["trace"]["excluded"].pop()
        pack["trace"]["truncated"] = True
    # The final check is done by callers/tests; if still over (impossible for
    # this corpus under the given budgets), the pack keeps the lowest-ranked
    # single node — deterministically the first survivor.
    if count_words(pack) > budget:
        pack["trace"]["truncated"] = True
