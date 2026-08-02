# engineering-encyclopedia

Versioned engineering knowledge nodes that make coding-agent reasoning
inspectable and provable.

## What is actually known

This project was measured, and the measurement was itself audited three
times. What is known, stated without advocacy:

- **In-sample, the knowledge pack changes agent output.** On three tasks
  (idempotency, subprocess safety, atomic file replacement), the treatment
  arm out-scored control on all six provider×task cells across two
  providers (DeepSeek, Mistral), and a placebo arm (a structurally
  identical pack with irrelevant content) sat at or below control on four
  of the six cells and only slightly above on the other two (Mistral e2
  +0.40, Mistral e3 +0.20) — far below the treatment deltas — so the
  in-sample effect is reproducible and is not prompt structure.
- **Out-of-sample, it does not generalise.** Of six out-of-sample cells
  (e4/e5 at n=15 on two providers, plus E6), exactly **one** shows a clean
  knowledge effect (e4-Mistral, +3.07). One cell cannot carry a rule.
- **The corpus rule is unsupported out-of-sample**, and `review.*` does not
  demonstrate an effect. Both are retained only as hypotheses.
- **The instrument was caught failing three times** (the report
  contaminating the scored artifact; a pattern crediting the wrong
  construct; the E6 parser and a criterion that never fired). Two of the
  three reversed a result. Every number below is scored with the repaired
  instrument.

The full record — raw scores, before/after, the audit — is in
`experiments/RESULTS.md`; a one-page summary is in
`docs/EXPERIMENT_SUMMARY.md`.

## What it is

Coding agents already contain this knowledge; they fail anyway because it
is stored in weights — activated probabilistically, not directly
inspectable or patchable. This repository stores it as fixed, versioned, hashed YAML
nodes, retrieves it deterministically (SQLite FTS5 with a pure-Python
fallback), and composes a bounded context pack per request. The product is
the **Application Report**: an agent names the node it applied, the
question it answered, and where in the artifact it answered it. A
human can read exactly which node the agent relied on and correct that
node; a weight cannot be corrected.

Four properties drive every design decision: reliable retrieval,
inspectability, consistency across models, and anchoring against
confabulation (a fixed, hashed text against which plausible invention
becomes visible).

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

## Governance and record

`main` is protected (pull requests required, force pushes blocked,
deletion blocked, required status check `validate`). Judgement calls are
recorded in `DEVIATIONS.md`; the corpus rule's status in
`docs/CORPUS_RULE.md`; the one-cell analysis in
`docs/WORKING_CELL_ANALYSIS.md`.
