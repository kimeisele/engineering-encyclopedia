# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten per
task, thirty in total per run set. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

There are **two run sets**, recorded because the harness changed between
them:

- **Set A — original run** (`experiments/fixtures/`): scored the raw
  completion, including the Application Report.
- **Set B — corrected run** (`experiments/fixtures-corrected/`): the harness
  now separates report from artifact (`---APPLICATION_REPORT---` delimiter,
  `runner.extract_artifact`); the rubric scores only the code above the
  delimiter, never the report.

Both sets use the same provider (deepseek-v4-flash, thinking disabled) and
the same rubrics. Set A is kept as the evidence for why the change was made;
it is not deleted.

## Set A — original run (confounded)

| Task | Node under test | Control mean | Treatment mean | Delta |
|---|---|---|---|---|
| e1 | reliability.idempotency | 4.40 | 5.80 | 1.40 |
| e2 | python.processes.subprocess-safety | 3.80 | 3.80 | 0.00 |
| e3 | python.files.atomic-replacement | 5.00 | 6.00 | 1.00 |

Raw scores (min/max/mean/stdev):

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 4.40 | 0.55 |
| e1 treatment | 6 | 6 | 6 | 5 | 6 | 5 | 6 | 5.80 | 0.45 |
| e2 control | 3 | 3 | 6 | 3 | 4 | 3 | 6 | 3.80 | 1.30 |
| e2 treatment | 5 | 4 | 3 | 3 | 4 | 3 | 5 | 3.80 | 0.84 |
| e3 control | 6 | 5 | 4 | 6 | 4 | 4 | 6 | 5.00 | 1.00 |
| e3 treatment | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |

## Set B — corrected run (report separated from artifact)

| Task | Node under test | Control mean | Treatment mean | Delta |
|---|---|---|---|---|
| e1 | reliability.idempotency | 3.80 | 5.00 | 1.20 |
| e2 | python.processes.subprocess-safety | 3.60 | 4.00 | 0.40 |
| e3 | python.files.atomic-replacement | 5.60 | 6.00 | 0.40 |

Raw scores (min/max/mean/stdev):

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 5 | 3 | 3 | 4 | 4 | 3 | 5 | 3.80 | 0.84 |
| e1 treatment | 6 | 4 | 4 | 5 | 6 | 4 | 6 | 5.00 | 1.00 |
| e2 control | 2 | 5 | 5 | 3 | 3 | 2 | 5 | 3.60 | 1.34 |
| e2 treatment | 4 | 3 | 4 | 5 | 4 | 3 | 5 | 4.00 | 0.71 |
| e3 control | 6 | 5 | 5 | 6 | 6 | 5 | 6 | 5.60 | 0.55 |
| e3 treatment | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |

## E2, stated plainly

The corrected run shows a **small positive delta, not a null result**:
e2 treatment {4,3,4,5,4} → 4.00 vs control {2,5,5,3,3} → 3.60, +0.40, with
overlapping distributions — consistent with an effect smaller than the
n=5 noise, not with no effect. The earlier write-up attributed the original
0.00 to report-text contamination; re-scoring the original files with the
report extracted changes **no** criterion on **any** run (verified
criterion-by-criterion), so that attribution was wrong for Set A: the
original deficit was driven by code comments (e.g. a comment reading
"no shell=True" still matches the rubric's absent-pattern) and genuinely
absent criteria. The report-contamination defect is nevertheless real as a
contract issue — an artifact scored together with its own description breaks
any scanner whose patterns the report's verbatim questions happen to match —
and is documented as node `testing.evaluation-contamination`. The corrected
harness is the valid protocol; Set A remains as the confounded evidence.

## Limitation

One provider (deepseek-v4-flash, thinking disabled), n=5 per arm, three
tasks, one rubric per task, two independent run sets. These results are a
**signal, not proof**: the sample is small, the rubric is a fixed string
checklist whose absent-patterns also match code comments, and no
cross-provider or cross-seed generalisation is claimed.

## Run records

Set A (original): DeepSeek Flash via the DeepSeek API, model
`deepseek-v4-flash`, thinking disabled; 2026-08-01;
`experiments/fixtures/manifest.jsonl` (30 runs).

Set B (corrected): same provider and configuration; treatment prompts gained
the `---APPLICATION_REPORT---` delimiter instruction; 2026-08-01;
`experiments/fixtures-corrected/manifest.jsonl` (30 runs). 15/15 treatment
outputs used the delimiter; 7 were extractable as YAML and 6 verified with
`encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`
(the rest failed with report-format errors — altered/omitted questions,
unparseable YAML — recorded as evidence about agent behaviour).

Rubrics: `experiments/rubrics/`, fixed before the runs; score = count of
satisfied boolean criteria. `runner.py score` applies `extract_artifact`
before scoring; `runner.py summarize <fixtures-dir>` regenerates the per-set
table from a manifest.
