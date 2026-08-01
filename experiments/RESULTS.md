# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm per
provider. Rubrics are fixed and deterministic (`experiments/rubrics/`);
the score is the count of satisfied criteria. Scoring pipeline v2:
`runner.py score` applies `extract_artifact` (report excluded) and
`strip_comments` (Python `#` comments removed) before the rubric.

**Three arms per provider, unpooled:**

- **control** — task prompt only
- **treatment** — task + knowledge pack + report instruction
- **placebo** — task + a structurally identical pack whose content is a node
  irrelevant to the task (`observability.error-context`), same slot count,
  same number of questions, same formatting (`experiments/packs-placebo/`,
  prompts within ~1% of the treatment prompts in length)

Five run sets: Set A (DeepSeek, original harness, confounded — kept as
evidence), Set B (DeepSeek, corrected), Set C (Mistral, corrected),
Set P-DS (DeepSeek placebo), Set P-MR (Mistral placebo).

## Three arms, per provider (final pipeline)

| Task | Provider | Control | Treatment | Placebo | T−C | P−C |
|---|---|---|---|---|---|---|
| e1 idempotency | DeepSeek | 3.80 | 4.80 | 2.20 | +1.00 | −1.60 |
| e1 idempotency | Mistral | 2.80 | 4.60 | 2.40 | +1.80 | −0.40 |
| e2 subprocess-safety | DeepSeek | 3.60 | 5.00 | 2.80 | +1.40 | −0.80 |
| e2 subprocess-safety | Mistral | 3.60 | 5.00 | 4.80 | +1.40 | +1.20 |
| e3 atomic-replacement | DeepSeek | 5.60 | 6.00 | 5.20 | +0.40 | −0.40 |
| e3 atomic-replacement | Mistral | 1.40 | 5.80 | 1.40 | +4.40 | 0.00 |

## Raw scores per arm (final pipeline)

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | mean | stdev |
|---|---|---|---|---|---|---|---|
| e1 DeepSeek control | 5 | 3 | 3 | 4 | 4 | 3.80 | 0.84 |
| e1 DeepSeek treatment | 6 | 3 | 4 | 5 | 6 | 4.80 | 1.30 |
| e1 DeepSeek placebo | 2 | 2 | 3 | 2 | 2 | 2.20 | 0.45 |
| e1 Mistral control | 4 | 3 | 2 | 3 | 2 | 2.80 | 0.84 |
| e1 Mistral treatment | 5 | 5 | 3 | 4 | 6 | 4.60 | 1.14 |
| e1 Mistral placebo | 2 | 2 | 2 | 2 | 4 | 2.40 | 0.89 |
| e2 DeepSeek control | 2 | 5 | 5 | 3 | 3 | 3.60 | 1.34 |
| e2 DeepSeek treatment | 5 | 4 | 5 | 6 | 5 | 5.00 | 0.71 |
| e2 DeepSeek placebo | 3 | 1 | 2 | 3 | 5 | 2.80 | 1.48 |
| e2 Mistral control | 4 | 2 | 4 | 4 | 4 | 3.60 | 0.89 |
| e2 Mistral treatment | 5 | 5 | 5 | 5 | 5 | 5.00 | 0.00 |
| e2 Mistral placebo | 5 | 5 | 5 | 4 | 5 | 4.80 | 0.45 |
| e3 DeepSeek control | 6 | 5 | 5 | 6 | 6 | 5.60 | 0.55 |
| e3 DeepSeek treatment | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |
| e3 DeepSeek placebo | 5 | 6 | 5 | 5 | 5 | 5.20 | 0.45 |
| e3 Mistral control | 1 | 2 | 1 | 2 | 1 | 1.40 | 0.55 |
| e3 Mistral treatment | 5 | 6 | 6 | 6 | 6 | 5.80 | 0.45 |
| e3 Mistral placebo | 2 | 1 | 1 | 1 | 2 | 1.40 | 0.55 |

## Placebo verdict — does the effect come from the knowledge or from the prompt?

**The placebo matches control, not treatment, on five of the six
task×provider cells; on one cell (Mistral E2) the placebo sits at the
treatment level.** Concretely:

- Placebo ≈ control (or below) on: DeepSeek e1 (2.20 vs control 3.80,
  treatment 4.80), DeepSeek e2 (2.80 vs 3.60, 5.00), DeepSeek e3 (5.20 vs
  5.60, 6.00), Mistral e1 (2.40 vs 2.80, 4.60), Mistral e3 (1.40 = 1.40,
  5.80). On those cells a longer, structured prompt alone did **not**
  reproduce the treatment effect — the knowledge is doing the work, and on
  two cells (DeepSeek e1, e2) placebo scored *below* control.
- Placebo ≈ treatment on: **Mistral e2** (placebo 4.80, treatment 5.00,
  control 3.60). Criterion-level, both the placebo and the treatment push
  Mistral's e2 code toward the list-argv style that its control runs miss;
  the treatment additionally satisfies `validation_or_whitelist` in most
  runs (5/5) while the placebo does not. A structural component cannot be
  ruled out for that one cell.

So the thesis — the knowledge nodes, not prompt length, produce the effect —
holds in five of six cells and is **not clean** on Mistral E2; that cell is
reported exactly as it came out and must not be generalised away.

## E2, stated plainly

After comment stripping, E2 shows a treatment delta of +1.40 (DeepSeek
corrected), +1.40 (Mistral) and +1.00 (Set A), comparable to E1 — the small
deltas reported earlier were suppressed by the models' own comments. The
placebo arm complicates the interpretation on Mistral (placebo 4.80 ≈
treatment 5.00 > control 3.60): part of Mistral's E2 improvement is
structural. On DeepSeek the placebo is below control (2.80), so there the
E2 effect is knowledge-driven.

## Limitation

Two providers, n=5 per arm, three tasks, one rubric per task, five run
sets. These results are a **signal, not proof**: the samples are small, the
rubric is a fixed string checklist, and one cell (Mistral E2) shows a
placebo effect that must not be smoothed over.

## Run records

- Set A: DeepSeek, `deepseek-v4-flash`, thinking disabled, original harness
  (confounded); `experiments/fixtures/manifest.jsonl`.
- Set B: DeepSeek, corrected harness (delimiter + extraction);
  `experiments/fixtures-corrected/manifest.jsonl`.
- Set C: Mistral, `mistral-small-latest`, corrected harness;
  `experiments/fixtures-mistral/manifest.jsonl`.
- Set P-DS: DeepSeek placebo (15 runs);
  `experiments/fixtures-placebo/manifest.jsonl`.
- Set P-MR: Mistral placebo (15 runs);
  `experiments/fixtures-placebo-mistral/manifest.jsonl`.
- All runs 2026-08-01; adapter `experiments/provider_chat_completions.py`
  (generic, vendor-free) via `ENCYCLOPEDIA_RUNNER`.
- Placebo packs: `experiments/make_placebo_packs.py` →
  `experiments/packs-placebo/<task>.yaml`; prompts
  `experiments/tasks/<task>-placebo.txt` (same slot count, question count
  and formatting as treatment; content from `observability.error-context`).

Rubrics: `experiments/rubrics/`, fixed before the runs. `runner.py score`
applies extraction + comment stripping; `runner.py summarize <fixtures-dir>`
regenerates a per-set three-arm table from a manifest.
