"""Keyword retrieval: SQLite FTS5 (mandatory) with a pure-Python fallback.

Section 5 contract:
- SQLite FTS5 is the primary backend, with BM25 ranking and the field
  weights ``intent_signals 4.0, keywords 3.0, title 2.0, remainder 1.0``.
- If the interpreter's ``sqlite3`` lacks FTS5, a deterministic pure-Python
  token-overlap scorer with the same field weights is used. The active path
  is reported in ``trace.retrieval_backend``.
- Determinism is per backend: within one backend, the same query, corpus and
  options produce byte-identical output; ties break by ascending id.
  Determinism is never asserted across backends.
- The ``ENCYCLOPEDIA_BACKEND`` environment variable may force a backend
  (``fts5`` or ``token-overlap``); this exists for testing only, there are no
  CLI flags for it.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Dict, List, Optional, Set, Tuple

from .loader import Node

# (field name, weight) — weights per Section 5.
FIELDS: Tuple[Tuple[str, float], ...] = (
    ("title", 2.0),
    ("summary", 1.0),
    ("intent_signals", 4.0),
    ("keywords", 3.0),
    ("techniques", 1.0),
    ("risks", 1.0),
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens, dropping single-character tokens.

    Identical tokenisation is used by both backends and by the pack
    composer's relevance lines, keeping the whole pipeline deterministic.
    """
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= 2]


def fts5_available() -> bool:
    """True when the interpreter's sqlite3 supports FTS5 virtual tables."""
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE _probe USING fts5(x)")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False


def _field_text(node: Node) -> Dict[str, str]:
    """Flatten the indexed fields of a node to searchable text."""
    data = node.data
    return {
        "title": str(data.get("title", "")),
        "summary": str(data.get("summary", "")),
        "intent_signals": " ".join(data.get("intent_signals", []) or []),
        "keywords": " ".join(data.get("keywords", []) or []),
        "techniques": " ".join(data.get("techniques", []) or []),
        "risks": " ".join(data.get("risks", []) or []),
    }


class RetrievalIndex:
    """Ranked keyword index over the corpus.

    ``backend`` is ``"fts5"`` or ``"token-overlap"`` and is reported to the
    caller; scores are an artefact of the backend and must never be compared
    across backends.
    """

    def __init__(self, nodes: List[Node], backend: Optional[str] = None):
        self.nodes = {node.id: node for node in nodes}
        self.ordered_ids = [node.id for node in sorted(nodes, key=lambda n: n.id)]
        if backend is None:
            backend = "fts5" if fts5_available() else "token-overlap"
        if backend not in ("fts5", "token-overlap"):
            raise ValueError(f"unknown retrieval backend: {backend}")
        self.backend = backend
        if backend == "fts5":
            self._build_fts5(nodes)
        else:
            self._build_token_overlap(nodes)

    # -- construction -----------------------------------------------------

    def _build_fts5(self, nodes: List[Node]) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            "CREATE VIRTUAL TABLE nodes USING fts5("
            "node_id UNINDEXED, title, summary, intent_signals, keywords,"
            " techniques, risks)"
        )
        with self._conn:
            for node in nodes:
                field = _field_text(node)
                self._conn.execute(
                    "INSERT INTO nodes (node_id, title, summary, intent_signals,"
                    " keywords, techniques, risks) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        node.id,
                        field["title"],
                        field["summary"],
                        field["intent_signals"],
                        field["keywords"],
                        field["techniques"],
                        field["risks"],
                    ),
                )

    def _build_token_overlap(self, nodes: List[Node]) -> None:
        self._tokens: Dict[str, Dict[str, Set[str]]] = {}
        for node in nodes:
            field = _field_text(node)
            self._tokens[node.id] = {
                name: set(tokenize(field[name])) for name, _ in FIELDS
            }

    # -- search ------------------------------------------------------------

    def search(self, query: str) -> List[Tuple[str, float]]:
        """Ranked ``[(node_id, score)]``, best first; ties by ascending id.

        ``score`` is higher-is-better within a backend. An empty query (no
        tokens) returns all nodes tied at 0.0, ordered by id.
        """
        if self.backend == "fts5":
            return self._search_fts5(query)
        return self._search_token_overlap(query)

    def _search_fts5(self, query: str) -> List[Tuple[str, float]]:
        terms = tokenize(query)
        if not terms:
            return [(node_id, 0.0) for node_id in self.ordered_ids]
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        rows = self._conn.execute(
            # One weight per table column, including the UNINDEXED node_id
            # column: node_id 0.0, title 2.0, summary 1.0, intent_signals 4.0,
            # keywords 3.0, techniques 1.0, risks 1.0.
            "SELECT node_id, bm25(nodes, 0.0, 2.0, 1.0, 4.0, 3.0, 1.0, 1.0) AS rank"
            " FROM nodes WHERE nodes MATCH ? ORDER BY rank ASC, node_id ASC",
            (match,),
        ).fetchall()
        # bm25 returns negative scores with more-negative = better; flip so
        # the public contract is uniformly "higher is better".
        return [(node_id, -rank) for node_id, rank in rows]

    def _search_token_overlap(self, query: str) -> List[Tuple[str, float]]:
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return [(node_id, 0.0) for node_id in self.ordered_ids]
        scored: List[Tuple[str, float]] = []
        for node_id in self.ordered_ids:
            score = 0.0
            for field_name, weight in FIELDS:
                score += weight * len(query_tokens & self._tokens[node_id][field_name])
            scored.append((node_id, score / (len(query_tokens) + 1.0)))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored


def default_backend() -> str:
    """The backend a fresh index will select."""
    return "fts5" if fts5_available() else "token-overlap"
