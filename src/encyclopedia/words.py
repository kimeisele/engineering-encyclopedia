"""Deterministic word counting over parsed YAML values.

Used for the Section 3 and Section 6 hard limits (``summary`` <= 70 words,
whole node file <= 500 words, pack detail budgets, ``answer`` <= 40 words).
"""

from __future__ import annotations

import re
from typing import Any

_WS_TOKEN_RE = re.compile(r"\S+")


def count_words(value: Any) -> int:
    """Count whitespace-separated tokens across all string scalars in *value*.

    Dict keys are not counted; only scalar values are. Nested lists and dicts
    are walked recursively.
    """
    if isinstance(value, str):
        return len(_WS_TOKEN_RE.findall(value))
    if isinstance(value, dict):
        return sum(count_words(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(count_words(v) for v in value)
    return 0
