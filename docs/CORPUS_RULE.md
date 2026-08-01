# Corpus rule — which knowledge deserves a node

Derived from the Section 8 experiment (`experiments/RESULTS.md`) and recorded
here to steer future corpus growth. Status: **working hypothesis — a signal,
not proof** (one provider, n=5 per arm, three tasks).

## The rule

A node earns a place in the corpus when applying the knowledge requires a
**state or design decision** by the writer: deciding what identifies one
operation, where completeness is recorded, what invalidates an entry, who
owns a write. A node does not earn a place when the correct behaviour is a
**memorised idiom** the model already emits without deliberation — a fixed
API shape or canonical call form.

Operational test for a candidate node: if its questions can be answered by
recall ("always do X"), it is an idiom and stays out of the corpus; if its
questions force a choice ("what identifies X", "where is Y recorded", "who
can claim Z"), it qualifies.

## Evidence from the experiment (raw scores)

| Task | Node | Type | Control raw | Treatment raw | Delta |
|---|---|---|---|---|---|
| E1 | reliability.idempotency | decision — what identifies one operation | {4,4,5,5,4} → 4.40 | {6,6,6,5,6} → 5.80 | +1.40 |
| E2 | python.processes.subprocess-safety | idiom — pass argv, never shell=True | {3,3,6,3,4} → 3.80 | {5,4,3,3,4} → 3.80 | 0.00 |
| E3 | python.files.atomic-replacement | decision — where durability is recorded | {6,5,4,6,4} → 5.00 | {6,6,6,6,6} → 6.00 | +1.00 |

The two decision-type tasks moved in the treatment arm (+1.40 and +1.00);
the idiom-type task did not (0.00). Two caveats keep this a hypothesis
rather than a proof: E2's 0.00 delta is confounded by a rubric blind spot
(the embedded application_report trips the absent-patterns, see
`experiments/RESULTS.md`), and E3's control baseline is already 5.00/6.00,
so its headroom was small. Within those limits, the data **supports** the
decision-vs-idiom rule; nothing in the data contradicts it.

## Consequence of this change

The corpus grows from eight to fifteen nodes, all chosen by this rule because
they require a decision rather than recall:

- `reliability.outbox-pattern` — what durably records the intent, and what
  identifies a row as published;
- `performance.cache-invalidation` — what identifies a cached entry, and
  what invalidates it;
- `testing.evaluation-contamination` — where the artifact ends and its own
  description begins (discovered in the E2 analysis; the report reproduces
  the check strings verbatim, so an artifact scored together with its
  description is contaminated);
- `reliability.circuit-breaker` — what counts as a failure and when the
  circuit opens (a model that knows the pattern still retries through an
  outage);
- `reliability.dead-letter-queue` — what happens when the retry budget is
  exhausted (a model that knows the concept still drops or retries forever);
- `observability.correlation-id` — what identifies one request end to end
  and how it is propagated (a model that knows tracing still logs without an
  id or regenerates it per hop);
- `concurrency.locking-strategy` — which locking strategy and what version
  detects conflict (a model that knows locks still locks everything or
  nothing).

Each of the last four is reachable by relations from the existing corpus
(circuit-breaker and dead-letter-queue from `reliability.retry-semantics`,
correlation-id from `observability.error-context`, locking-strategy from
`concurrency.race-conditions`), and all four are out-of-sample candidates for
the experiment (the tasks are written after the nodes, not alongside them).

## How the rule is applied later

- Every candidate node passes the operational test above before it is
  written; idiom-type candidates are rejected or folded into an existing
  node.
- The experiment evidence (frozen packs, treatment prompts, fixture
  manifest) is pinned to the eight-node corpus it ran against
  (DEVIATIONS D10). Edits to those eight nodes, or a new corpus change,
  require a conscious decision to regenerate `experiments/packs/` and the
  `-treatment` prompts; the frozen-pack test enforces this.
