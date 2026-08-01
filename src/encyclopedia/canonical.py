"""Deterministic serialisation and content hashing.

Byte-determinism is the foundation of the whole system: node content hashes,
the corpus revision, ``context_pack_hash`` and the per-backend byte-identical
output guarantee all rest on the canonical form defined here.
"""

from __future__ import annotations

import hashlib
from typing import Any

import yaml


class _CanonicalDumper(yaml.SafeDumper):
    """SafeDumper that never emits anchors or aliases (input is plain data)."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def canonical_yaml(data: Any) -> str:
    """Serialise *data* to byte-deterministic YAML.

    Keys are sorted, block style is used throughout and Unicode is kept
    as-is. Comments and anchors never survive parsing, so the output is
    fully determined by the parsed value alone.
    """
    return yaml.dump(
        data,
        Dumper=_CanonicalDumper,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )


def canonical_bytes(data: Any) -> bytes:
    """UTF-8 bytes of the canonical YAML serialisation of *data*."""
    return canonical_yaml(data).encode("utf-8")


def sha256_prefix(data: bytes, length: int = 12) -> str:
    """First *length* hex characters of the SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()[:length]


def node_content_hash(node: dict) -> str:
    """Content hash of a parsed node: SHA-256[:12] over its canonical form.

    Computed by the loader, never stored in the node file.
    """
    return sha256_prefix(canonical_bytes(node))
