# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten
per task, thirty in total. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

## Summary table

| Task | Node under test | Control mean | Treatment mean | Delta |
|---|---|---|---|---|
| e1 | reliability.idempotency | 4.40 | 5.80 | 1.40 |
| e2 | python.processes.subprocess-safety | 3.80 | 3.80 | 0.00 |
| e3 | python.files.atomic-replacement | 5.00 | 6.00 | 1.00 |

## Raw scores per run

n=5 per arm; spread is the sample standard deviation.

| Task / arm | run-1 | run-2 | run-3 | run-4 | run-5 | min | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| e1 control | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 4.40 | 0.55 |
| e1 treatment | 6 | 6 | 6 | 5 | 6 | 5 | 6 | 5.80 | 0.45 |
| e2 control | 3 | 3 | 6 | 3 | 4 | 3 | 6 | 3.80 | 1.30 |
| e2 treatment | 5 | 4 | 3 | 3 | 4 | 3 | 5 | 3.80 | 0.84 |
| e3 control | 6 | 5 | 4 | 6 | 4 | 4 | 6 | 5.00 | 1.00 |
| e3 treatment | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6.00 | 0.00 |

## E2: ceiling effect or rubric blind spot?

Not a ceiling effect — control averages only 3.80/6.00 with raw scores
{3,3,3,4,6} (one run at the rubric maximum, so headroom exists) — it is a
rubric blind spot: the rubric scans the raw completion, and the treatment
outputs embed the application_report, whose verbatim pack questions repeat
the banned phrases (e.g. `shell=True` occurs in e2/treatment/run-1's report
and a comment while its code is a safe `subprocess.run(["git","branch",branch])`
list call), so the absent-criteria fail on self-description and both arms
land on the identical 3.80 mean with overlapping distributions
({3,3,3,4,6} vs {3,3,4,4,5}). The criterion breakdown confirms it:
treatment satisfies no rubric criterion more often than control
(no_shell_true 0/5 vs 1/5, no_command_interpolation 1/5 vs 2/5), so the
0.00 delta is a measurement artefact of the fixed rubric, not evidence
that the pack had no effect.

## Limitation

One provider (deepseek-v4-flash, thinking disabled), n=5 per arm, three
tasks, one rubric per task. These results are a **signal, not proof**: the
sample is small, the rubric is a fixed string checklist with a documented
blind spot (E2), and no cross-provider or cross-seed generalisation is
claimed.

## Run record

- Provider: DeepSeek Flash via the DeepSeek API (OpenAI-compatible
  chat/completions), model `deepseek-v4-flash`, endpoint
  `https://api.deepseek.com/chat/completions`.
- Adapter: `experiments/provider_chat_completions.py` (generic, vendor-free),
  invoked through `ENCYCLOPEDIA_RUNNER`. Thinking was disabled
  (`thinking: {type: disabled}`): with reasoning enabled the model exhausts
  the token budget on `reasoning_content` and returns an empty `content`, so
  every run uses the same disabled-thinking configuration.
- Date: 2026-08-01. 30/30 runs recorded in
  `experiments/fixtures/manifest.jsonl` (per-run model command and date).
- Rubrics: `experiments/rubrics/`, fixed before the runs; score = count of
  satisfied boolean criteria.
- Application Report check (treatment arm): 14 of 15 outputs contained an
  `application_report`; 12 were extractable as YAML and 8 fully verified
  with `encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`.
  The others failed verification with report-format errors (altered or
  omitted questions, duplicated dispositions, unparseable YAML) — recorded
  here as evidence about agent behaviour, not about the harness.

How results are produced: `runner.py run` records each completion and a
manifest entry; `runner.py summarize <fixtures-dir> --out experiments/RESULTS.md`
regenerates this table from the manifest. Treatment-arm reports can be
verified with `encyclopedia verify-report <report> --pack experiments/packs/<task>.yaml`.
