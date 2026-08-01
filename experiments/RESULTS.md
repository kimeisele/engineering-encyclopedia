# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten per
task, thirty in total per run set. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

Three run sets are recorded, because the harness and the provider changed:

- **Set A — DeepSeek, original harness** (`experiments/fixtures/`): scored
  the raw completion, including the Application Report (confounded).
- **Set B — DeepSeek, corrected harness** (`experiments/fixtures-corrected/`):
  the harness separates report from artifact
  (`---APPLICATION_REPORT---` delimiter, `runner.extract_artifact`); the
  rubric scores only the code above the boundary.
- **Set C — Mistral, corrected harness** (`experiments/fixtures-mistral/`):
  same corrected protocol, second provider (`mistral-small-latest`).

Sets A and B answer "does the pack change the outcome"; Set C answers
"does the effect hold across models". Results are **not pooled** across
providers. Set A is kept as the evidence for why the harness changed; it is
not deleted.

## Summary tables (means)

| Task | Node under test | Set A (DeepSeek, confounded) | Set B (DeepSeek, corrected) | Set C (Mistral, corrected) |
|---|---|---|---|---|
| e1 | reliability.idempotency | 4.40 / 5.80 (+1.40) | 3.80 / 5.00 (+1.20) | 2.80 / 5.00 (+2.20) |
| e2 | python.processes.subprocess-safety | 3.80 / 3.80 (0.00) | 3.60 / 4.00 (+0.40) | 3.60 / 4.00 (+0.40) |
| e3 | python.files.atomic-replacement | 5.00 / 6.00 (+1.00) | 5.60 / 6.00 (+0.40) | 1.40 / 5.80 (+4.40) |

(control mean / treatment mean; delta in parentheses)

## Raw scores per set

Set A (DeepSeek, original):

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 4.40 | 0.55 |
| e1 treatment | 6 | 6 | 6 | 5 | 6 | 5 | 6 | 5.80 | 0.45 |
| e2 control | 3 | 3 | 6 | 3 | 4 | 3 | 6 | 3.80 | 1.30 |
| e2 treatment | 5 | 4 | 3 | 3 | 4 | 3 | 5 | 3.80 | 0.84 |
| e3 control | 6 | 5 | 4 | 6 | 4 | 4 | 6 | 5.00 | 1.00 |
| e3 treatment | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |

Set B (DeepSeek, corrected):

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 5 | 3 | 3 | 4 | 4 | 3 | 5 | 3.80 | 0.84 |
| e1 treatment | 6 | 4 | 4 | 5 | 6 | 4 | 6 | 5.00 | 1.00 |
| e2 control | 2 | 5 | 5 | 3 | 3 | 2 | 5 | 3.60 | 1.34 |
| e2 treatment | 4 | 3 | 4 | 5 | 4 | 3 | 5 | 4.00 | 0.71 |
| e3 control | 6 | 5 | 5 | 6 | 6 | 5 | 6 | 5.60 | 0.55 |
| e3 treatment | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |

Set C (Mistral, corrected):

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 4 | 3 | 2 | 3 | 2 | 2 | 4 | 2.80 | 0.84 |
| e1 treatment | 5 | 6 | 4 | 4 | 6 | 4 | 6 | 5.00 | 1.00 |
| e2 control | 4 | 2 | 4 | 4 | 4 | 2 | 4 | 3.60 | 0.89 |
| e2 treatment | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4.00 | 0.00 |
| e3 control | 1 | 2 | 1 | 2 | 1 | 1 | 2 | 1.40 | 0.55 |
| e3 treatment | 5 | 6 | 6 | 6 | 6 | 5 | 6 | 5.80 | 0.45 |

## E2, stated plainly

The corrected E2 result is a **small positive delta that replicates across
both providers, with overlapping distributions** — not a null result, and
not a large effect: DeepSeek treatment {4,3,4,5,4} → 4.00 vs control
{2,5,5,3,3} → 3.60 (+0.40); Mistral treatment {4,4,4,4,4} → 4.00 vs control
{4,2,4,4,4} → 3.60 (+0.40). Two measurement caveats keep even this small
delta soft: the rubric's absent-patterns also match code comments (all four
Mistral treatment artifacts contain a line like `# Run the command without
shell=True to prevent injection`, which fails `no_shell_true`), and the
Mistral model ignored the delimiter (0/15) — the `application_report:`
fallback recovered the boundary in 14/15 outputs, and one run (e2/2) wrote
its report without that key, so its whole completion was scored. The
earlier attribution of Set A's 0.00 to report text was wrong (re-scoring Set
A with the report extracted changes no criterion on any run); the
report-contamination defect is nevertheless real as a contract issue and is
documented as node `testing.evaluation-contamination`.

## Does the effect hold across models?

Yes, in direction: the treatment arm out-scored control on all three tasks
with both providers, and the largest effect is on the same task for both
(e1 +1.20/+2.20; e3 +0.40/+4.40 — Mistral's control without the pack is
dramatically worse on e3, 1.40). E2 is the weakest effect on both (+0.40),
consistent with the decision-vs-idiom corpus rule (E2 is the idiom task).
The magnitude is provider-specific, which is why results are not pooled.

## Limitation

Two providers, n=5 per arm, three tasks, one rubric per task, three run
sets. These results are a **signal, not proof**: the samples are small, the
rubric is a fixed string checklist whose absent-patterns also match code
comments, Mistral did not follow the delimiter (boundary recovered by
fallback), and no further cross-seed generalisation is claimed.

## Run records

- Set A: DeepSeek Flash via the DeepSeek API, `deepseek-v4-flash`, thinking
  disabled; 2026-08-01; `experiments/fixtures/manifest.jsonl`.
- Set B: same provider and configuration; treatment prompts gained the
  `---APPLICATION_REPORT---` delimiter instruction; 2026-08-01;
  `experiments/fixtures-corrected/manifest.jsonl`. 15/15 used the delimiter.
- Set C: Mistral via the Mistral API, `mistral-small-latest`; same corrected
  prompts; 2026-08-01; `experiments/fixtures-mistral/manifest.jsonl`.
  0/15 used the delimiter; 14/15 reports recovered by the `application_report:`
  fallback.
- Adapter: `experiments/provider_chat_completions.py` (generic, vendor-free),
  invoked through `ENCYCLOPEDIA_RUNNER` — no vendor name in code.
- Rubrics: `experiments/rubrics/`, fixed before the runs; score = count of
  satisfied boolean criteria. `runner.py score` applies `extract_artifact`
  before scoring; `runner.py summarize <fixtures-dir>` regenerates the
  per-set table from a manifest.

How results are produced: `runner.py run` records each completion and a
manifest entry. Treatment-arm reports can be verified with
`encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`.
