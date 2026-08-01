# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten
per task, thirty in total. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

Status: **harness shipped, no completions recorded yet.**

Reason: the 30 completions are run by the owner against their own
provider via `ENCYCLOPEDIA_RUNNER`; this repository does not execute
an external model. No synthetic fixtures exist and none may be added:
recorded fixtures are only genuine outputs of an identified external
agent run, with model and date noted (Section 8).

| Task | Node under test | Control mean | Treatment mean | Delta |
|---|---|---|---|---|
| e1 | reliability.idempotency | _ | _ | _ |
| e2 | python.processes.subprocess-safety | _ | _ | _ |
| e3 | python.files.atomic-replacement | _ | _ | _ |

How results are produced: `runner.py run` records each completion and a
manifest entry; `runner.py summarize <fixtures-dir> --out experiments/RESULTS.md`
regenerates this table from the manifest. Treatment-arm reports can be
verified with `encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`.
