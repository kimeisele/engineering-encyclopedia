"""Loading of knowledge nodes and taxonomy from disk.

The repository root is resolved from this module's location
(``<root>/src/encyclopedia/``), so the tool works from a clean checkout
without configuration. Tests and embedding environments can override the
locations with ``ENCYCLOPEDIA_KNOWLEDGE_DIR`` / ``ENCYCLOPEDIA_TAXONOMY_DIR``.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .canonical import node_content_hash

def _resolve_repo_root() -> Path:
    """Locate the corpus root (knowledge/ + taxonomy/).

    Resolution order:
    1. ENCYCLOPEDIA_ROOT env var (explicit override, used by embeddings)
    2. package-relative location — the source-checkout layout
       (<root>/src/encyclopedia/), used by tests and clean checkouts
    3. current working directory — an installed wheel run from the repo root
    4. a clear error, never a silent guess
    """
    env = os.environ.get("ENCYCLOPEDIA_ROOT")
    if env:
        return Path(env)
    package_relative = Path(__file__).resolve().parents[2]
    if (package_relative / "knowledge").is_dir() and (
        package_relative / "taxonomy"
    ).is_dir():
        return package_relative
    cwd = Path.cwd()
    if (cwd / "knowledge").is_dir() and (cwd / "taxonomy").is_dir():
        return cwd
    raise FileNotFoundError(
        "cannot locate the corpus (knowledge/ and taxonomy/ directories): "
        "run from the repository root or set ENCYCLOPEDIA_ROOT"
    )


REPO_ROOT = _resolve_repo_root()

KNOWLEDGE_DIR = Path(
    os.environ.get("ENCYCLOPEDIA_KNOWLEDGE_DIR", str(REPO_ROOT / "knowledge"))
)
TAXONOMY_DIR = Path(
    os.environ.get("ENCYCLOPEDIA_TAXONOMY_DIR", str(REPO_ROOT / "taxonomy"))
)

# Denial-of-service guards for imported YAML: imported YAML is data, but a
# hostile or corrupted file must fail cleanly instead of exhausting the
# process (deep nesting raises RecursionError; alias expansion and huge
# documents scale memory and CPU without bound).
MAX_YAML_BYTES = 2 * 1024 * 1024
MAX_YAML_NODES = 1_000_000


class CappedSafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects documents beyond a node budget.

    ``SafeLoader`` never constructs executable types; this only adds a
    complexity ceiling on top.
    """

    def __init__(self, stream):
        super().__init__(stream)
        self._nodes = 0

    def construct_object(self, node, deep=False):
        self._nodes += 1
        if self._nodes > MAX_YAML_NODES:
            raise yaml.YAMLError("document too complex")
        return super().construct_object(node, deep)


@dataclass(frozen=True)
class Node:
    """A loaded knowledge node with its computed content hash.

    ``version`` is the raw YAML value; the validator enforces the integer
    type so a string version surfaces as a validation error, not a crash.
    """

    id: str
    version: Any
    title: str
    kind: str
    status: str
    data: Dict[str, Any]
    content_hash: str
    path: Path


def load_yaml_file(path: Path, max_bytes: int = MAX_YAML_BYTES) -> Any:
    """Load a YAML file with ``yaml.safe_load`` only.

    Imported YAML is data, never configuration, never executable. Files are
    capped in size and node count so a malformed or hostile document fails
    cleanly (``yaml.YAMLError`` / ``ValueError``) instead of exhausting the
    process.
    """
    try:
        if path.stat().st_size > max_bytes:
            raise ValueError(
                f"YAML file too large: {path} ({path.stat().st_size} bytes, "
                f"max {max_bytes})"
            )
    except OSError:
        raise
    with open(path, "r", encoding="utf-8") as handle:
        try:
            return yaml.load(handle, Loader=CappedSafeLoader)
        except RecursionError as exc:
            raise yaml.YAMLError("document too deeply nested") from exc


def load_nodes(knowledge_dir: Path = KNOWLEDGE_DIR) -> List[Node]:
    """Load every ``*.yaml`` node under *knowledge_dir*, sorted by id.

    The content hash is computed by the loader and never read from a file.
    """
    nodes: List[Node] = []
    for path in sorted(knowledge_dir.rglob("*.yaml")):
        data = load_yaml_file(path)
        if not isinstance(data, dict):
            raise ValueError(f"node file is not a mapping: {path}")
        if "id" not in data:
            raise ValueError(f"node file has no id: {path}")
        nodes.append(
            Node(
                id=str(data["id"]),
                # The raw value is kept: the validator enforces the integer
                # type. Coercing here would hide a schema violation and crash
                # on non-numeric values instead of failing validation.
                version=data["version"],
                title=str(data["title"]),
                kind=str(data["kind"]),
                status=str(data["status"]),
                data=data,
                content_hash=node_content_hash(data),
                path=path,
            )
        )
    nodes.sort(key=lambda node: node.id)
    return nodes


def load_taxonomy(taxonomy_dir: Path = TAXONOMY_DIR) -> Dict[str, Any]:
    """Load the three taxonomy enumerations as parsed YAML."""
    result: Dict[str, Any] = {}
    for name in ("node-kinds", "contexts", "relation-types"):
        result[name] = load_yaml_file(taxonomy_dir / f"{name}.yaml")
    return result


def corpus_revision(nodes: List[Node]) -> str:
    """sha256[:12] over the sorted corpus content hashes.

    ``knowledge_revision`` identifies the exact set of node texts an agent
    was shown; the Application Report must echo it.
    """
    digest = hashlib.sha256()
    for node in nodes:
        digest.update(node.content_hash.encode("ascii"))
    return digest.hexdigest()[:12]
