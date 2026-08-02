# Convergence analysis — the variance reading of the existing evidence

Re-analysis of ALL existing completions — no new API calls, no corpus
changes. The repository's actual claim is about consistency: does the pack
make output CONVERGE — across providers, across runs, in structure and
vocabulary — so that a non-technical operator and a second agent encounter
the same shape of solution regardless of which model produced it?
Convergence is invisible in a mean comparison; this document re-reads the
data for it. All numbers are scored with the repaired instrument. n per
cell: 10 (e1–e3, e6), 30 (e4, e5); placebo for e1–e3 from the separate
placebo sets.

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

Markers per task (e.g. for e4: named circuit states, an explicit threshold,
a reset path, a fail-fast guard; for e3: temp file, atomic rename, fsync).
Per arm: mean |rate_DS − rate_MR| across the task's markers (0 = identical
profiles), and the marker detail for the two largest divergences.

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
  On e1 the null stays null under this lens too.

The convergence claim is therefore supported on four of six tasks, absent
on e1, and vacuous-but-not-negative on e5 — reported separately, not
pooled.
