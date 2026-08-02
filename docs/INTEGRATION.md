# Integration: consuming a context pack from another repository

Minimal integration path. Another repository can use the knowledge base
without reading its source. The measured effect comes from the pack alone:
handing the pack to the agent *before* the work changes what it writes. No
report is required to get that effect — the report/verify flow below is an
optional audit variant. Everything below was run exactly as written.

## 1. Install

Requires Python 3.12+ (matching the repository's `pyproject.toml`). From
this repository:

```sh
pip install .
```

The only runtime dependency is PyYAML; everything works offline. The wheel
carries the corpus (`knowledge/`, `taxonomy/`), so the installed
`encyclopedia` works from any directory — including this repository's own.
To use a different corpus, set `ENCYCLOPEDIA_ROOT` to a directory
containing `knowledge/` and `taxonomy/`.

## 2. The simple path: generate a pack

```sh
encyclopedia query "make sure this worker doesn't process the same job twice" --detail guidance > pack.yaml
```

The output is a context pack: the request, `knowledge_revision` (the
corpus's identity), `context_pack_hash` (a SHA-256[:12] of the pack's
content), `retrieval_backend`, `trace` (which nodes were selected and
excluded, and whether the budget truncated any), and `context_pack` with
`primary` and `supporting` nodes. Every node carries `id`, `version`,
`hash`, `relevance`, `summary`, `questions`, `does_not_imply` and `risks`.
The excerpt below is abridged to the nodes and fields that matter here
(this run: corpus revision `96bf58e88848`):

```yaml
knowledge_revision: 96bf58e88848
context_pack_hash: f70a481b60ee
context_pack:
  primary:
    - id: reliability.idempotency
      version: 1
      hash: 4cbc1598c0d7
      questions:
        - What value identifies one logical operation, and where does it come from?
        - Where is completion recorded, and is that record durable before the effect?
        - What state remains after a failure between effect and completion record?
        - Can two workers observe the same operation as not-yet-done simultaneously?
```

## 3. The simple path: hand the pack to the agent, done

Give the agent the request plus the pack, verbatim, and let it work. That
is the whole integration: the pack changes what the model writes. Keep the
exact `pack.yaml` you handed over — if you later want auditability, the
report binds to it via `context_pack_hash`, so verify against that file,
not a regenerated one. (The pack's exact content depends on the retrieval
backend active in the generating environment — `retrieval_backend`: `fts5`
or `token-overlap` — which is why you verify against the file you
actually passed.)

## 4. Optional: auditable evidence

Where you want proof that the agent engaged with the pack — not just the
effect — ask the agent to return, next to its work, an `application_report`
in this shape:

```yaml
application_report:
  knowledge_revision: <from the pack>
  context_pack_hash: <from the pack>
  applied:
    - node: <node id from the pack>
      version: <version>
      hash: <hash>
      questions_answered:
        - question: "<a question of that node, verbatim>"
          answer: "<non-empty, at most 40 words>"
          location: "<file:line where you applied it>"
      unanswered:
        - question: "<a question of that node, verbatim>"
          reason: "<why you did not answer it>"
  not_applied:
    - node: <any other node id from the pack>
      reason: "<why you did not apply it>"
```

The contract: every pack node appears exactly once across `applied` and
`not_applied`; questions are copied verbatim; every question of an applied
node is answered with a location or explicitly marked unanswered.

Verify — offline, no model:

```sh
encyclopedia verify-report report.yaml --pack pack.yaml
```

Exit code 0 on pass, 1 on failure, with a machine-readable failure list.
`verify-report` proves: the report's `context_pack_hash` and
`knowledge_revision` match the pack; the pack's content hashes to its
declared hash; every pack node is disposed of exactly once; every question
of an applied node is answered or marked unanswered; answers are non-empty
and ≤ 40 words with a non-empty location; `not_applied` entries carry a
reason.

## Worked end-to-end example (run exactly as written)

**Simple path.** `encyclopedia query "make sure this worker doesn't process
the same job twice" --detail guidance > pack.yaml` — pack `f70a481b60ee`,
revision `96bf58e88848`, nodes: reliability.idempotency,
concurrency.race-conditions, concurrency.locking-strategy,
python.files.atomic-replacement, reliability.retry-semantics. Hand the pack
to the agent with the request. Done.

**Optional variant: verified.** Ask for the `application_report` and get
this (the agent applies `reliability.idempotency`; other pack nodes are
`not_applied`):

```yaml
application_report:
  knowledge_revision: 96bf58e88848
  context_pack_hash: f70a481b60ee
  applied:
    - node: reliability.idempotency
      version: 1
      hash: 4cbc1598c0d7
      questions_answered:
        - question: Where is completion recorded, and is that record durable before the effect?
          answer: In the processed_jobs table, written in the same transaction as the charge.
          location: worker.py:41
      unanswered:
        - question: What value identifies one logical operation, and where does it come from?
          reason: The job id is the identity; no separate key is introduced.
        - question: What state remains after a failure between effect and completion record?
          reason: The failure path aborts before the charge; nothing to reconcile.
        - question: Can two workers observe the same operation as not-yet-done simultaneously?
          reason: Single-worker deployment in this task; not applicable.
  not_applied:
    - node: concurrency.race-conditions
      reason: No shared mutable state in this change.
    - node: concurrency.locking-strategy
      reason: No concurrent writers in this change.
    - node: python.files.atomic-replacement
      reason: No file writes in this change.
    - node: reliability.retry-semantics
      reason: No retries in this change.
```

`encyclopedia verify-report report.yaml --pack pack.yaml` → exit 0,
`ok: true`.

A failure looks like this — if the agent silently skips a question:

```yaml
failures:
  - code: omitted_question
    detail: 'reliability.idempotency: question ''Can two workers observe the
      same operation as not-yet-done simultaneously?'' is neither answered
      nor unanswered'
ok: false
```

Exit code 1. A skipped question, a dropped pack node, an altered question
or a claim without a location all fail verification instead of passing
silently.
