# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten per
task, thirty in total per run set. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

Scoring pipeline v2 (this file): `runner.py score` applies
`extract_artifact` **and** `strip_comments` before the rubric runs —
the report is excluded (boundary: `---APPLICATION_REPORT---` delimiter, else
`application_report:` / `knowledge_revision:` / `context_pack_hash:`), and
Python `#` comments are removed so the rubric's absent-patterns are not
tripped by prose the model wrote as comments (e.g. a line `# no shell=True`
in an otherwise safe artifact).

Three run sets are recorded:

- **Set A — DeepSeek, original harness** (`experiments/fixtures/`): scored
  the raw completion, including the Application Report (confounded).
- **Set B — DeepSeek, corrected harness** (`experiments/fixtures-corrected/`).
- **Set C — Mistral, corrected harness** (`experiments/fixtures-mistral/`),
  second provider (`mistral-small-latest`).

## Before / after — comment stripping (Sets A/B/C)

"Before" = extraction only (the previously recorded numbers); "after" =
extraction + comment stripping. Control mean / treatment mean / delta.

| Set | Task | Before | After |
|---|---|---|---|
| A | e1 idempotency | 4.40 / 5.80 (+1.40) | 4.00 / 5.60 (+1.60) |
| A | e2 subprocess-safety | 3.80 / 3.80 (0.00) | 3.80 / 4.80 (+1.00) |
| A | e3 atomic-replacement | 5.00 / 6.00 (+1.00) | 5.00 / 6.00 (+1.00) |
| B | e1 idempotency | 3.80 / 5.00 (+1.20) | 3.80 / 4.80 (+1.00) |
| B | e2 subprocess-safety | 3.60 / 4.00 (+0.40) | 3.60 / 5.00 (+1.40) |
| B | e3 atomic-replacement | 5.60 / 6.00 (+0.40) | 5.60 / 6.00 (+0.40) |
| C | e1 idempotency | 2.80 / 5.00 (+2.20) | 2.80 / 4.60 (+1.80) |
| C | e2 subprocess-safety | 3.60 / 4.00 (+0.40) | 3.60 / 5.00 (+1.40) |
| C | e3 atomic-replacement | 1.40 / 5.80 (+4.40) | 1.40 / 5.80 (+4.40) |

## E2, stated plainly

Comment stripping changes the E2 picture materially: the treatment delta on
E2 is **+1.00 (Set A), +1.40 (Set B), +1.40 (Set C)** — the earlier small
deltas (+0.00 to +0.40) were depressed by the models writing comments like
`# no shell=True to prevent injection` in otherwise safe artifacts, which
the absent-patterns counted as violations. After stripping comments, the E2
treatment effect is comparable to E1's.

## Report-boundary robustness

The boundary now cuts at the first of: the `---APPLICATION_REPORT---`
delimiter, or the report's mandatory YAML keys `application_report:`,
`knowledge_revision:`, `context_pack_hash:`. This recovers the one previously
missed report (Mistral e2/2, which started directly at `knowledge_revision:`
without the container key). Residual limit, documented because it cannot be
removed by detection: a model that emits a report containing none of these
markers cannot have its report separated — chat completions return a single
free-form string, so no protocol can force the delimiter; `verify-report`
remains the final check.

## Limitation

Two providers, n=5 per arm, three tasks, one rubric per task. These results
are a **signal, not proof**: the samples are small, the rubric is a fixed
string checklist, and the scoring pipeline changed twice during this cycle
(extraction, then comment stripping), with both versions recorded here.

## Run records

- Set A: DeepSeek Flash via the DeepSeek API, `deepseek-v4-flash`, thinking
  disabled; 2026-08-01; `experiments/fixtures/manifest.jsonl`.
- Set B: same provider and configuration; treatment prompts gained the
  `---APPLICATION_REPORT---` delimiter; 2026-08-01;
  `experiments/fixtures-corrected/manifest.jsonl`.
- Set C: Mistral via the Mistral API, `mistral-small-latest`; 2026-08-01;
  `experiments/fixtures-mistral/manifest.jsonl`.

Rubrics: `experiments/rubrics/`, fixed before the runs. `runner.py score`
applies extraction + comment stripping; `runner.py summarize <fixtures-dir>`
regenerates the per-set table from a manifest.
