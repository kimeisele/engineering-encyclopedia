"""Command-line interface (Section 9 of the founding brief).

Commands: validate, list, show, search, related, query, verify-report.
No other commands. No router flags of any kind.

Every emitted document is serialised with sorted keys, so repeated identical
invocations produce byte-identical output within a retrieval backend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

import yaml

from . import __version__
from .loader import REPO_ROOT, corpus_revision, load_nodes, load_taxonomy
from .pack import PackOptions, compose_pack
from .report import verify_report
from .retrieval import RetrievalIndex
from .validate import validate_all


def _emit(data: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(
            yaml.safe_dump(
                data, sort_keys=True, allow_unicode=True, default_flow_style=False
            ),
            end="",
        )


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
        help="output format (default yaml)",
    )


def _query_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--detail",
        choices=("compact", "guidance", "full"),
        default="guidance",
        help="pack detail level (default guidance)",
    )
    parser.add_argument(
        "--max-primary",
        type=int,
        default=3,
        help="max primary nodes (default 3, capped at 3)",
    )
    parser.add_argument(
        "--max-supporting",
        type=int,
        default=3,
        help="max supporting nodes (default 3, capped at 3)",
    )
    parser.add_argument("--language", default=None, help="filter by node language")
    parser.add_argument("--project-type", default=None, help="filter by node project type")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="encyclopedia",
        description="Versioned engineering knowledge nodes that make coding-agent "
        "reasoning inspectable and provable.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the corpus and taxonomy")
    _common_options(p)

    p = sub.add_parser("list", help="list all nodes")
    _common_options(p)

    p = sub.add_parser("show", help="show one node in full")
    p.add_argument("node_id", help="node id, e.g. reliability.idempotency")
    _common_options(p)

    p = sub.add_parser("search", help="ranked keyword search")
    p.add_argument("text", help="search text")
    _common_options(p)

    p = sub.add_parser("related", help="graph neighbours of a node")
    p.add_argument("node_id", help="node id")
    _common_options(p)

    p = sub.add_parser("query", help="compose a context pack for a request")
    p.add_argument("request", help="the request to pack knowledge for")
    _common_options(p)
    _query_options(p)

    p = sub.add_parser("verify-report", help="verify an Application Report against its pack")
    p.add_argument("report_path", help="path to the application report YAML")
    p.add_argument("--pack", required=True, help="path to the context pack YAML (mandatory)")
    _common_options(p)

    return parser


def _load_all() -> Any:
    """Shared loader: nodes, taxonomy, index. Lazy so `validate` stays cheap."""
    nodes = load_nodes()
    index = RetrievalIndex(nodes)
    return nodes, index


def cmd_validate(args: argparse.Namespace) -> int:
    ok, errors, nodes = validate_all()
    if not ok:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(nodes)} nodes validated (revision {corpus_revision(nodes)})")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    nodes, _ = _load_all()
    _emit(
        [
            {
                "id": node.id,
                "title": node.title,
                "version": node.version,
                "status": node.status,
                "hash": node.content_hash,
            }
            for node in nodes
        ],
        args.format,
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    nodes, _ = _load_all()
    node = next((n for n in nodes if n.id == args.node_id), None)
    if node is None:
        print(f"unknown node id: {args.node_id}", file=sys.stderr)
        return 1
    data = dict(node.data)
    data["content_hash"] = node.content_hash
    _emit(data, args.format)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    nodes, index = _load_all()
    ranked = index.search(args.text)
    by_id = {node.id: node for node in nodes}
    _emit(
        [
            {"id": node_id, "title": by_id[node_id].title, "score": round(score, 6)}
            for node_id, score in ranked
        ],
        args.format,
    )
    return 0


def cmd_related(args: argparse.Namespace) -> int:
    nodes, _ = _load_all()
    node = next((n for n in nodes if n.id == args.node_id), None)
    if node is None:
        print(f"unknown node id: {args.node_id}", file=sys.stderr)
        return 1
    by_id = {node.id: node for node in nodes}
    relations = node.data.get("relations") or {}
    outgoing = {
        target: key
        for key in ("related", "requires_consideration_of")
        for target in relations.get(key, []) or []
    }
    result = []
    for neighbour in sorted(by_id):
        if neighbour == node.id:
            continue
        relation = outgoing.get(neighbour)
        if relation is not None:
            result.append(
                {
                    "id": neighbour,
                    "title": by_id[neighbour].title,
                    "relation": relation,
                    "direction": "outgoing",
                }
            )
            continue
        other = by_id[neighbour].data.get("relations") or {}
        for key in ("related", "requires_consideration_of"):
            if node.id in (other.get(key, []) or []):
                result.append(
                    {
                        "id": neighbour,
                        "title": by_id[neighbour].title,
                        "relation": key,
                        "direction": "incoming",
                    }
                )
                break
    _emit(result, args.format)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    nodes, index = _load_all()
    options = PackOptions(
        detail=args.detail,
        max_primary=args.max_primary,
        max_supporting=args.max_supporting,
        language=args.language,
        project_type=args.project_type,
    )
    pack = compose_pack(nodes, index, args.request, options)
    _emit(pack, args.format)
    return 0


def cmd_verify_report(args: argparse.Namespace) -> int:
    nodes, _ = _load_all()
    ok, failures, corpus = verify_report(
        Path(args.report_path), Path(args.pack), nodes
    )
    _emit({"ok": ok, "failures": failures, "corpus": corpus}, args.format)
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    commands = {
        "validate": cmd_validate,
        "list": cmd_list,
        "show": cmd_show,
        "search": cmd_search,
        "related": cmd_related,
        "query": cmd_query,
        "verify-report": cmd_verify_report,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
