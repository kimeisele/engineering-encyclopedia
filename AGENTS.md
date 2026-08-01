# AGENTS.md — engineering-encyclopedia

Guidance for agents working in this repository. Read the founding brief
(`docs/FOUNDING BRIEF v2.md`) before changing anything structural.

## What this is

A local-first, offline, deterministic knowledge base of versioned YAML
engineering nodes, a keyword retrieval layer, a bounded context pack composer,
a machine-checkable Application Report format, and a three-case experiment
harness. The product is the Application Report, not the retrieval engine.

## Commands

```sh
python -m unittest discover        # full test suite (unittest only, no pytest)
python -m compileall src           # compile check
python -m pip install -e .         # dev install (gives the `encyclopedia` CLI)
encyclopedia validate              # validate corpus + taxonomy
encyclopedia query "<request>"     # emit a context pack
encyclopedia verify-report <report> --pack <pack>   # verify an application report
```

## Layout

- `src/encyclopedia/` — package. Modules: `loader` (load nodes, compute content
  hashes), `canonical` (deterministic serialisation + hashing), `validate`
  (schema + hard limits), `retrieval` (FTS5 with token-overlap fallback),
  `pack` (context pack composer), `report` (`verify-report`), `cli`.
- `knowledge/<area>/<name>.yaml` — the sixteen nodes. `knowledge/LICENSE` is CC
  BY 4.0, do not touch.
- `taxonomy/` — enumerations (`node-kinds`, `contexts`, `relation-types`).
- `evaluations/queries.yaml` — 10 regression queries with required /
  forbidden-to-dominate node IDs.
- `experiments/` — standalone harness (rubrics, prompts, runner). It must NOT
  import `src/`, is not run by unittest, is not part of CI.
- `tests/` — unittest suite.

## Conventions

- Python 3.12+, PyYAML + stdlib only. No new runtime dependencies, ever.
- Nodes are data: `yaml.safe_load` only, never executed.
- Content hash = SHA-256 over the canonically serialised node (keys sorted,
  no comments), first 12 hex chars. Computed by the loader, never stored.
- Determinism is per retrieval backend. The same query, corpus and options
  produce byte-identical output; ties break by ascending `id`. Determinism is
  never asserted across backends.
- Hard numeric limits (Section 3 and 6 of the brief) are enforced by the
  validator and by tests — do not relax them to make a suite pass.
- `context_pack_hash` is SHA-256 over the canonically serialised pack with the
  `context_pack_hash` field omitted, first 12 hex chars.

## Decision rule (Section 15)

Every file must serve one of: node quality, the citation mechanism,
provability, the experiment, or reproducibility. If something serves none of
them, it does not belong in v1.

## Never (Section 1 negative list, binding)

No LLM routers or model calls in the query path. No embeddings, vector stores,
RAG frameworks, graph databases. No network access during `query`, `search`,
`show`, `related`, `validate`. No federation, sync, manifests, trust models,
signatures. No web servers, daemons, orchestration. No scheduled workflows.
No empty placeholder files/directories/modules. No nodes beyond the sixteen.
Adding anything from this list is a defect, not initiative.

## Experiments

The harness is provider-agnostic: the concrete model command comes from the
`ENCYCLOPEDIA_RUNNER` environment variable, never hardcoded; no vendor name
appears in code, config or docs. It is invoked manually — not by unittest, not
by CI. The network ban applies to the query path only; the harness may use the
network. See `experiments/README.md`.
