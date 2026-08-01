# Experiment results

Three tasks from the founding brief, Section 8, plus two out-of-sample
tasks. Five runs per arm per provider. Rubrics are fixed and deterministic
(`experiments/rubrics/`); the score is the count of satisfied criteria.
Scoring pipeline: `runner.py score` applies `extract_artifact` (report
excluded) and `strip_comments` (Python `#` comments removed) before the
rubric, and the rubrics were **repaired in the instrument-fix cycle**
(see the instrument-repair section below). All numbers below are scored
with the repaired rubrics unless stated otherwise.

**Three arms per provider, unpooled:** control / treatment / placebo (a
structurally identical pack with irrelevant content).

## In-sample (e1–e3)

| Task | Provider | Control | Treatment | Placebo | T−C | P−C |
|---|---|---|---|---|---|---|
| e1 idempotency | DeepSeek | 4.00 | 4.80 | 2.20 | +0.80 | −1.80 |
| e1 idempotency | Mistral | 2.80 | 4.80 | 2.40 | +2.00 | −0.40 |
| e2 subprocess-safety | DeepSeek | 4.40 | 5.60 | 3.80 | +1.20 | −0.60 |
| e2 subprocess-safety | Mistral | 4.40 | 6.00 | 4.80 | +1.60 | +0.40 |
| e3 atomic-replacement | DeepSeek | 4.60 | 6.00 | 4.40 | +1.40 | −0.20 |
| e3 atomic-replacement | Mistral | 0.40 | 6.00 | 0.60 | +5.60 | +0.20 |

Treatment exceeds control on all six cells. The placebo sits at or below
control on DeepSeek (all three) and slightly above control on Mistral e2
(+0.40) and e3 (+0.20) — far below the treatment. The in-sample anomaly is
attenuated with the repaired instrument.

## Out-of-sample (e4, e5) — reported separately

Fresh tasks on two later nodes (`reliability.circuit-breaker`,
`observability.correlation-id`); same pipeline, not merged with the
in-sample tables.

| Task | Provider | Control | Treatment | Placebo | T−C | P−C |
|---|---|---|---|---|---|---|
| e4 circuit-breaker | DeepSeek | 5.60 | 5.60 | 4.80 | 0.00 | −0.80 |
| e4 circuit-breaker | Mistral | 2.80 | 6.00 | 2.60 | +3.20 | −0.20 |
| e5 correlation-id | DeepSeek | 5.00 | 5.40 | 5.00 | +0.40 | 0.00 |
| e5 correlation-id | Mistral | 5.40 | 5.60 | 4.20 | +0.20 | −1.20 |

With the repaired instrument the out-of-sample result is: **one clear
effect** (e4-Mistral +3.20, placebo at control), **one ceiling-limited flat
cell** (e4-DeepSeek, control 5.60/6.00), and **two cells too small to call**
(e5-DeepSeek +0.40, e5-Mistral +0.20 — both inside within-arm spread at
n=5; e5-Mistral moved from −1.40 to +0.20 by rescoring alone, so it is not
evidence in either direction). The instrument-caught negative cell is gone,
but "three of four positive" would overstate the data: the rule **survives
in direction** on a single strong cell, with modest support. The
corpus-rule judgment on these numbers is stated in the judgment section
below.

## Instrument repair (rubric audit) — before/after

The first out-of-sample test found a defect in the measurement, not in the
knowledge. This is the **second time this project has caught its own
instrument** (first: the Application Report contaminating the scored
artifact — node 11; second: the `id_in_logs` pattern crediting a method
definition). That is what out-of-sample tests are for.

What was fixed (all five rubrics audited; `blind_to` statements added to
every criterion):

- **e5 `id_in_logs` (the negative-cell cause):** the old pattern
  `log\w*\(...` matched method definitions (`log_success(self, trace_id,
  ...)` — this was the positive match in the best control run) and could
  not match idiomatic `logger.error(...)` because of the dot between
  `logger` and `error`. Now: `(log|logger|logging)\w*\.(debug|info|warning|error|critical)\s*\([^)]*(request_id|correlation_id|trace_id)`.
- **e5 `id_propagated` / `downstream_reuses`:** widened to the
  explicit-parameter design the node itself recommends (passing a request
  object), not only headers.
- **e5 `errors_carry_id`:** widened to context-dict attachment.
- **e3 `atomic_rename`:** tightened — a bare `.replace(` no longer credits
  `str.replace()`.
- **e3 `no_direct_truncate`:** widened to variable paths, then refined so
  temp-file writes (`os.fdopen`, tmp/temp names) are not false-flagged;
  the rubric self-test then caught a residual bug (a bare `path` identifier
  was not flagged) and it was fixed.
- **e3 `same_directory` / `failure_cleanup`:** widened (`with_name`,
  context-manager cleanup).
- **e4 `breaker_state` / `fail_fast_when_open`:** tightened — a bare word
  `open` no longer credits file-open() calls or prose.
- **e4 `success_resets`:** rebalanced — the old pattern credited a variable
  named `reset_timeout`; the new pattern credits a reset/close mechanism
  (`state = "closed"`, `_reset(`, `failures = 0`).
- **e1 `effect_guarded_by_record`:** widened to unique-constraint and
  conflict-avoidance designs.
- **e2 `argv_list`:** widened to a prebuilt argv variable.

Before → after (mean per arm; before = the previously published
final-pipeline numbers, after = repaired rubrics, same completions):

| Set | Task | Before (C/T/P) | After (C/T/P) |
|---|---|---|---|
| A | e1 | 4.00 / 5.60 / – | 4.00 / 5.60 / – |
| A | e2 | 3.80 / 4.80 / – | 4.40 / 5.20 / – |
| A | e3 | 5.00 / 6.00 / – | 3.60 / 6.00 / – |
| B | e1 | 3.80 / 4.80 / 2.20 | 4.00 / 4.80 / 2.20 |
| B | e2 | 3.60 / 5.00 / 2.80 | 4.40 / 5.60 / 3.80 |
| B | e3 | 5.60 / 6.00 / 5.20 | 4.60 / 6.00 / 4.40 |
| C | e1 | 2.80 / 4.60 / 2.40 | 2.80 / 4.80 / 2.40 |
| C | e2 | 3.60 / 5.00 / 4.80 | 4.40 / 6.00 / 4.80 |
| C | e3 | 1.40 / 5.80 / 1.40 | 0.40 / 6.00 / 0.60 |
| OOS-DS | e4 | 5.40 / 5.20 / 4.80 | 5.60 / 5.60 / 4.80 |
| OOS-DS | e5 | 4.80 / 4.80 / 4.40 | 5.00 / 5.40 / 5.00 |
| OOS-MR | e4 | 2.80 / 6.00 / 2.60 | 2.80 / 6.00 / 2.60 |
| OOS-MR | e5 | 5.20 / 3.80 / 2.80 | 5.40 / 5.60 / 4.20 |

Material moves: e3 control drops (the instrument now catches variable-path
truncating writes — the exact failure e3 targets), e2 rises (argv_list
widening), and e5 treatment rises on both providers (id_in_logs repair) —
turning the Mistral e5 negative cell into +0.20.

**Re-runs (item 3): none.** The repair changes the scoring, not the
completions: every cell that moved (e3 control, e2, e5 treatment on both
providers) was corrected by re-scoring the same completions. Re-running
those cells would replace valid completions with new samples for no
measurement reason, so no cell was re-run.

## E2, stated plainly

After comment stripping and the rubric repair, the E2 treatment delta is
+0.80 (Set A), +1.20 (DeepSeek corrected), +1.60 (Mistral) — the effect is
positive on both providers and larger than the earlier small deltas, which
were suppressed by model-written comments and by the argv_list pattern
missing variable-list designs.

## Statistics — one honest sentence per task

Spread is the pooled within-arm standard deviation (n=5 each); "exceeds"
means the delta is larger than that spread. No significance testing.

- **e1:** treatment exceeds the spread on Mistral (+2.00 vs ~1.0) and is
  inside it on DeepSeek (+0.80 vs ~1.1), with placebo at or below control
  both — e1 is not prompt length, but its DeepSeek size is n=5 noise.
- **e2:** treatment exceeds the spread on both providers (+1.20 / +1.60 vs
  ~1.0), while the Mistral placebo sits +0.40 above control (down from the
  earlier +1.20 anomaly) — e2 is mostly knowledge, with a residual small
  structural component on Mistral.
- **e3:** treatment far exceeds the spread on Mistral (+5.60) and exceeds
  it on DeepSeek (+1.40), with placebo at or below control on both — e3 is
  the cleanest knowledge effect.

Out-of-sample, per cell: e4-Mistral +3.20 exceeds its spread; e4-DeepSeek
0.00 is a ceiling pair (control 5.60/6.00); e5-DeepSeek +0.40 and
e5-Mistral +0.20 are inside their spreads. Plain: **one clear effect, one
ceiling-limited flat cell, two cells too small to call** — none negative,
but only e4-Mistral is evidence of an effect.

## Out-of-sample at n=15 (item 2)

The e4/e5 cells were extended from n=5 to n=15 per arm (same prompts,
same repaired rubrics; runs 6–15 appended to the existing sets, no run
replaced). 120 additional completions, 0 failures.

| Cell | C (n=15) | T (n=15) | P (n=15) | T−C | P−C | pooled sd(T,C) | clears spread? |
|---|---|---|---|---|---|---|---|
| e4 DeepSeek | 5.40 | 5.60 | 5.00 | +0.20 | −0.40 | 0.57 | no (ceiling: control 5.40/6) |
| e4 Mistral | 2.87 | 5.93 | 2.40 | +3.07 | −0.47 | 1.01 | **yes** |
| e5 DeepSeek | 5.07 | 5.07 | 5.00 | +0.00 | −0.07 | 0.92 | no |
| e5 Mistral | 5.33 | 5.60 | 3.87 | +0.27 | −1.47 | 0.73 | no |

**Which deltas clear within-arm spread and which still do not:** only
e4-Mistral (+3.07 vs 1.01, with the placebo −0.47 at control). e4-DeepSeek
(+0.20 vs 0.57) is a ceiling pair, e5-DeepSeek is exactly 0.00, and
e5-Mistral (+0.27 vs 0.73) remains too small to call. Extending to n=15 did
**not** rescue the two e5 cells; the out-of-sample support for the corpus
rule still rests on a single node (circuit-breaker on Mistral). Placebo at
n=15 is at or below control on all four cells.

## Judgment (corpus rule, repaired instrument, n=15)

With the repaired instrument and n=15 per out-of-sample arm, the corpus
rule **survives out-of-sample in direction**, and that is the defensible
claim: only one cell clears within-arm spread (e4-Mistral +3.07 with the
placebo at control). e4-DeepSeek is a ceiling pair (control 5.40/6.00), and
the two e5 cells (0.00, +0.27) are inside within-arm spread even at n=15 —
"three of four positive" would overstate the data. The rule is supported,
not proven, and control-arm headroom (the flat cell) remains the plainest
caveat.

## Limitation

Two providers, n=5 per arm, five tasks (three in-sample, two
out-of-sample), one rubric per task, several run sets. These results are a
**signal, not proof**; the rubrics were repaired after the first
out-of-sample pass, and every number above is scored with the repaired
instrument (before/after recorded above).

## Run records

- Sets: A (`experiments/fixtures/`, DeepSeek, original harness, confounded),
  B (`experiments/fixtures-corrected/`, DeepSeek, corrected harness),
  C (`experiments/fixtures-mistral/`, Mistral), P-DS / P-MR (placebo arms),
  OOS-DS / OOS-MR (e4/e5, both providers). All 2026-08-01; manifests
  alongside the fixtures.
- Provider adapters: `experiments/provider_chat_completions.py` (generic,
  vendor-free) via `ENCYCLOPEDIA_RUNNER`; DeepSeek `deepseek-v4-flash`
  (thinking disabled) and Mistral `mistral-small-latest`.
- Rubrics: `experiments/rubrics/`, fixed before the runs, repaired in the
  instrument-fix cycle; every criterion carries a `blind_to` statement.
  `runner.py score` applies extraction + comment stripping;
  `runner.py summarize <fixtures-dir>` regenerates a per-set table.
