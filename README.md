# engineering-encyclopedia

Versioned engineering knowledge nodes that make coding-agent reasoning
inspectable and provable.

## What it is

Coding agents already contain this knowledge; they fail anyway because it
is stored in weights — activated probabilistically, not directly
inspectable or patchable. This repository stores it as fixed, versioned,
hashed YAML nodes, retrieves it deterministically (SQLite FTS5 with a
pure-Python fallback), and composes a bounded context pack per request.
The product is the **Application Report**: an agent names the node it
applied, the question it answered, and where in the artifact it answered
it. A human can read exactly which node the agent relied on and correct
that node; a weight cannot be corrected.

Four properties drive every design decision: reliable retrieval,
inspectability, consistency across models, and anchoring against
confabulation (a fixed, hashed text against which plausible invention
becomes visible).

## What is established

The primary claim is **convergence**: the pack makes agent output the same
shape across vendors and runs. In the full convergence re-analysis of all
six tasks' existing runs (in-sample e1–e3, plus the out-of-sample tasks
e4–e6), **convergence holds on four of six tasks** (e2, e3, e4, e6):
treatment collapses the between-provider gap, drives the providers'
criterion disagreements to 0/6 on five of six tasks (all but e1), and on
e3/e4 makes both providers emit the same structural constructs where
control had them completely apart. The placebo (a structurally identical
pack with irrelevant content) does not reproduce any of it, so the
convergence is not prompt structure. e1 is the exception; e5 was already
converged. In-sample, the pack also makes output better (treatment
out-scored control on all six e1–e3 cells) — but that is the secondary
result. The convergence claim is marked in-sample only: the pre-registered
fresh-task test returned NULL (below).

## What is not established

- **Out-of-sample convergence: NULL by pre-registered test.** Two fresh
  tasks (e7 locking-strategy, e8 cache-invalidation), markers and decision
  rule committed before any run: e7 passed both conditions, e8 failed the
  marker condition — treatment converged the means but **diverged the
  constructs** (DeepSeek adopted a version-in-key cache, Mistral dropped
  its TTL). Per the pre-registered rule the convergence claim is
  **in-sample only**. The e8 divergence is recorded as an observation,
  not a plain null: the node lists valid answers without deciding between
  them (`docs/UNDERDETERMINED_NODES.md`).
- **The corpus rule is unsupported out-of-sample** (retained only as a
  hypothesis), and `review.*` does not demonstrate an effect.
- **Out-of-sample quality: exactly one of six cells is clean**
  (e4-Mistral +3.07). The pack does not reliably make output better out of
  sample.

## The instrument

The measurement was corrected three times: the Application Report
contaminating the scored artifact; a pattern crediting the wrong construct;
the E6 parser and a criterion that never fired. **Two of the three
reversed a result.** Every number in this repository is scored with the
repaired instrument, before/after recorded.

## For a non-technical operator: using node questions as review questions

You do not need to read the code an agent produced to check whether it used
the knowledge. Each node carries `questions` — concrete, answerable
questions like "Where is completion recorded, and is that record durable
before the effect?" Use those questions as your review checklist against
work you cannot read yourself: the agent must answer each question **with a
location** (a file and a line where the answer can be found). An answer
without a location is not an answer.

`encyclopedia verify-report` makes this mechanical. It takes the agent's
report and the exact pack the agent was given, and proves — offline, with
no model involved — that:

- the report is bound to the pack it claims (hashes must match),
- every node in the pack appears exactly once, applied or explicitly
  not-applied (a node cannot be silently dropped),
- every question of an applied node is answered with a non-empty location,
  or explicitly marked unanswered (**no question can be skipped**),
- the questions are the node's own (altered wording fails).

Worked example. An agent was given the `reliability.idempotency` node and
returns this report fragment:

```yaml
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
```

`verify-report` checks the hash against the node, checks that the question
is the node's own (altered wording fails) with a non-empty answer and a
non-empty location such as `worker.py:41`, and confirms every other
question of the node was either answered or explicitly marked unanswered —
so a question that was skipped, or a claim without a location, fails
verification instead of passing silently.

## Install and use

Requires Python 3.12+; the only runtime dependency is PyYAML. Everything
works offline.

```sh
pip install .
encyclopedia validate
encyclopedia query "make sure this worker doesn't process the same job twice"
encyclopedia verify-report report.yaml --pack pack.yaml
```

Commands: `validate`, `list`, `show`, `search`, `related`, `query`,
`verify-report`. No other commands.

## Licensing

- **Code** (`src/`, `tests/`, `experiments/`): MIT — see `LICENSE`.
- **Knowledge content** (`knowledge/`, `taxonomy/`): CC BY 4.0 — see
  `knowledge/LICENSE`.

## Record

`main` is protected (pull requests required, force pushes blocked,
deletion blocked, required status check `validate`). The full experiment
record is in `experiments/RESULTS.md`; the one-page summary in
`docs/EXPERIMENT_SUMMARY.md`; judgement calls in `DEVIATIONS.md`.
