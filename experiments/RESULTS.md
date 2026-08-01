# Experiment results

Three tasks from the founding brief, Section 8. Five runs per arm, ten
per task, thirty in total. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.

Status: completions recorded; scores below are current as of the manifest.

| Task | Node under test | Control mean | Treatment mean | Delta |
|---|---|---|---|---|
| e1 | reliability.idempotency | 4.40 | 5.80 | 1.40 |
| e2 | python.processes.subprocess-safety | 3.80 | 3.80 | 0.00 |
| e3 | python.files.atomic-replacement | 5.00 | 6.00 | 1.00 |

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
