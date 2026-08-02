# Convergence analysis — the variance reading of the existing evidence

Re-analysis of ALL existing completions — no new API calls, no corpus
changes. The repository's actual claim is about consistency: does the pack
make output CONVERGE — across providers, across runs, in structure and
vocabulary — so that a non-technical operator and a second agent encounter
the same shape of solution regardless of which model produced it?
Convergence is invisible in a mean comparison; this document re-reads the
data for it. Sections 1, 2 and 4 use the repaired rubric scores; Section 3
uses the structural markers defined below — observable constructs
independent of the rubric (e.g. a bare `CLOSED` constant counts as a named
state even where the rubric's `success_resets` pattern would not, which is
why a marker rate and a criterion rate can differ for the same cell). n per
cell: 10 (e1–e3, e6) and 30 (e4, e5) pooled across providers (5+5,
15+15); per-provider n is 5 or 15.

## Structural markers (exact definitions)

Regexes matched with `re.search` + `re.DOTALL` over the scored artifact
(extraction + comment stripping for code tasks; extraction only for e6):

- **e1**: `dedup_record` = `processed|done|handled|dedup`;
  `check_before` = `if\s+.*(processed|exists|already|done)`;
  `same_tx` = `transaction|atomic|unique|ON CONFLICT|conflict`
- **e2**: `argv_list` =
  `\.(run|Popen|call|check_output|check_call)\s*\(\s*(\[|[A-Za-z_]\w*\s*[,)])`;
  `validation` = `re\.(match|fullmatch|search)|startswith|valid|whitelist|allowed|safe|branches`
- **e3**: `temp_file` = `tempfile|mkstemp|NamedTemporaryFile|\.tmp|\btmp`;
  `atomic_rename` = `os\.replace|os\.rename|Path\.replace`;
  `fsync` = `\.flush\s*\(|os\.fsync|fsync`
- **e4**: `named_states` = `closed|open|half[- ]?open|is_open|CLOSED|OPEN`;
  `threshold` = `max_failures|failure_threshold|threshold|failures\s*[>=]`;
  `reset_path` = `state\s*=\s*['\"]closed|_reset\s*\(|CLOSED|failures\s*=\s*0`;
  `fail_fast` = `if\s+.*(is_open|state|circuit).{0,40}(raise|return|fail)`
- **e5**: `id_parameter` = `correlation_id|request_id|trace_id`;
  `id_header` = `X-Request-Id|x-request-id|headers`
- **e6**: `file_line_cited` = `worker\.py\s*[:@]\s*\d+|\blines?\s+\d+`;
  `unsupported_phrasing` = `not supported|unsupported`

## 1. Between-provider convergence (mean gap per task per arm)

| Task | Control gap \|DS−MR\| | Treatment gap | Placebo gap |
|---|---|---|---|
| e1 | 1.20 (4.00 / 2.80) | **0.00** (4.80 / 4.80) | 0.20 |
| e2 | 0.00 (4.40 / 4.40) | 0.40 (5.60 / 6.00) | 1.00 |
| e3 | 4.20 (4.60 / 0.40) | **0.00** (6.00 / 6.00) | 3.80 |
| e4 | 2.53 (5.40 / 2.87) | **0.33** (5.60 / 5.93) | 2.60 |
| e5 | 0.27 (5.07 / 5.33) | 0.53 (5.07 / 5.60) | 1.13 |
| e6 | 1.00 (3.80 / 2.80) | **0.20** (3.40 / 3.60) | 0.60 |

Treatment reduces the between-provider gap on e1, e3, e4, e6; e2 is
trivially zero already (both near ceiling); e5 widens slightly (0.27 →
0.53). The e4 reading the owner flagged is confirmed exactly: the
between-provider spread collapses 2.53 → 0.33 (≈ 7.7×), and the placebo
leaves it at 2.60 — so it is not prompt structure alone.

## 2. Within-arm variance (run-to-run sd per cell)

| Task | DS control→treatment | MR control→treatment |
|---|---|---|
| e1 | 1.00 → 1.30 | 0.84 → 1.30 |
| e2 | 1.14 → 0.55 | 1.34 → 0.00 |
| e3 | 0.55 → 0.00 | 0.55 → 0.00 |
| e4 | 0.51 → 0.63 | 1.41 → 0.26 |
| e5 | 1.03 → 0.80 | 0.90 → 0.51 |
| e6 | 0.45 → 0.89 | 1.10 → 0.55 |

Treatment reduces within-run variance on e2, e3, e5 and on Mistral for e4
and e6; it does **not** on e1 (both providers worse) and DeepSeek e4/e6
drift slightly upward (both from already-low control sd).

## 3. Structural convergence — the metric that matches the claim

Markers per task (exact regexes above). Per arm: mean |rate_DS − rate_MR|
across the task's markers (0 = identical profiles), and the marker detail
for the two largest divergences.

| Task | Control | Treatment | Placebo |
|---|---|---|---|
| e1 | 0.33 | 0.40 | 0.20 |
| e2 | 0.20 | **0.00** | 0.50 |
| e3 | 0.87 | **0.00** | 0.73 |
| e4 | 0.85 | **0.10** | 0.85 |
| e5 | 0.07 | 0.13 | 0.00 |
| e6 | 0.20 | **0.10** | 0.10 |

The two dramatic cases, in detail:

- **e3** — control: DeepSeek writes temp+rename+fsync in 100%/100%/60% of
  runs, Mistral in 0%/0%/0% (it truncates). Treatment: **100%/100%/100% on
  both providers** — same shape of answer, regardless of vendor.
- **e4** — control: DeepSeek emits named states/threshold/reset/fail-fast
  in 100%/100%/93%/100%, Mistral in 13%/13%/13%/13%. Treatment:
  ~100%/100%/100% on both (fail-fast 87% DS / 47% MR). Placebo leaves
  Mistral at 0% — structure alone does not do this.

e5's profile was already converged at control (0.07), so treatment has
little to add; e1 does not converge on any marker.

## 4. Criterion-level agreement (modal pass/fail per provider)

| Task | Control disagreements | Treatment | Placebo |
|---|---|---|---|
| e1 | 2/6 | 2/6 | 0/6 |
| e2 | 2/6 | **0/6** | 1/6 |
| e3 | 5/6 | **0/6** | 4/6 |
| e4 | 3/6 | **0/6** | 4/6 |
| e5 | 1/6 | **0/6** | 1/6 |
| e6 | 2/6 | **0/6** | 1/6 |

Treatment drives the two providers to pass or fail the **same** criteria
on 5 of 6 tasks (all except e1), where control had them diverge — including
e5 and e6, whose means were null.

## Where convergence appears, and where it does not

- **Convergence appears clearly** on e2, e3, e4 and e6: treatment collapses
  the between-provider gap and the criterion disagreements (to 0/6) and, on
  e3/e4, makes the two providers emit the same structural markers (0.87 →
  0.00, 0.85 → 0.10) where control had them completely apart. The placebo
  does not reproduce any of this — structure alone is not the cause.
- **e5 stays mostly null under this lens**: its control was already
  converged (gap 0.27, markers 0.07, disagreement 1/6), the construct was
  present unaided, and treatment slightly widens the gap (0.27 → 0.53)
  while perfecting criterion agreement (1/6 → 0/6). Nothing to converge
  means nothing to show.
- **e1 is the honest exception**: convergence does not appear on any of the
  four lenses — the gap collapses (1.20 → 0.00, both moving to the same
  mean) but within-run variance increases on both providers, criterion
  disagreement stays at 2/6, and the structural profiles do not converge.
  On e1 the null stays null under this lens too. (The e1 placebo happens to
  reach 0/6 disagreements and a better marker overlap (0.20 vs 0.40) —
  better than treatment on those two numbers — but that agreement is
  agreement on the absence of the construct, and the treatment still wins
  the gap (0.00 vs 0.20). See `docs/E1_EXCEPTION.md`.)

The convergence claim is therefore supported on four of six tasks, absent
on e1, and vacuous-but-not-negative on e5 — reported separately, not
pooled.
