# Contributing

Guidance for humans writing nodes and touching this repository. Agents
working in the tree should read `AGENTS.md`; contributors should read this
file and the founding brief (`docs/FOUNDING BRIEF v2.md`).

## The decide-versus-list writing rule

Guidance with evidence — not a measured law. The pre-registered
convergence test (e7, e8) and the convergence re-analysis produced one
practical, evidence-backed observation about how nodes behave across
providers and runs:

**A node converges when it prescribes a primary technique, and does not
when it lists equivalent options with conditions the task cannot settle.**

- `python.files.atomic-replacement` and `reliability.circuit-breaker`
  prescribe: their techniques are headed by a singular decision (write a
  temp file, fsync, then `os.replace`; a rolling-window failure threshold
  with a single half-open probe). Both providers converged on the same
  constructs (structural markers 0.87 → 0.00 and 0.85 → 0.10).
- `performance.cache-invalidation` lists: version-in-key, explicit
  invalidation on writes, TTL-as-fallback, with `choose_when` conditions
  the task does not settle. The pre-registered e8 test showed the two
  providers moving in opposite directions (DeepSeek adopted version-in-key,
  Mistral dropped TTL) — an effect without a shared direction.

When writing a node:

- Make each question have **one answer the task must take**, carried by a
  prescribed primary technique.
- If you list alternatives, expect the node to underdetermine convergence:
  different models will pick different valid answers. Either decide, or
  accept that the node informs rather than converges.

Evidence: `docs/UNDERDETERMINED_NODES.md`,
`docs/CONVERGENCE_ANALYSIS.md`, `docs/CONVERGENCE_PREREGISTRATION_RESULTS.md`.

## Node schema and limits

Nodes live in `knowledge/<area>/<name>.yaml` and must satisfy the Section 3
bar: the required fields, hard limits (summary ≤ 70 words, whole file ≤ 500
words, any list entry ≤ 25 words, 4–12 intent signals, 3–6 questions), and
taxonomy values are enforced by `encyclopedia validate` and by the test
suite. Relations must resolve within the corpus.

## The rubric self-test is mandatory

Every rubric in `experiments/rubrics/` must have a positive and a negative
fixture per criterion in `tests/test_rubrics.py`; a criterion without
fixtures fails the suite. This exists because the measurement was corrected
three times — a rubric pattern that cannot be tested will not be reviewed
twice.

## Checks

```sh
python -m compileall src tests experiments/runner.py
python -m unittest discover
encyclopedia validate
```

`main` is protected: pull requests required, force pushes blocked,
deletion blocked, required status check `validate`. CI runs the four checks
above.

## Licensing

Code (`src/`, `tests/`, `experiments/`): MIT. Knowledge (`knowledge/`,
`taxonomy/`): CC BY 4.0. Do not move files between the two without
changing the license headers and files.
