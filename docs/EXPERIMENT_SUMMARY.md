# Experimental programme — honest summary

One page, no advocacy, no roadmap. Full numbers in
`experiments/RESULTS.md`; the corpus-rule status in
`docs/CORPUS_RULE.md`; the convergence re-analysis in
`docs/CONVERGENCE_ANALYSIS.md` and its pre-registered test in
`docs/CONVERGENCE_PREREGISTRATION_RESULTS.md`.

## What is established

**In-sample convergence (the primary claim), placebo-controlled.** In the
full convergence re-analysis of all six tasks' existing runs (in-sample
e1–e3, plus the out-of-sample tasks e4–e6), treatment converges the
output: **convergence holds on four of six tasks** (e2, e3, e4, e6), the
providers' criterion disagreements fall to 0/6 on five of six tasks (all
but e1), and on e3/e4 both providers emit the same structural constructs
where control had them completely apart. The placebo does not reproduce
this, so it is not prompt structure. In-sample the pack also makes output
better (treatment > control on all six e1–e3 cells). The convergence claim
is in-sample only (the pre-registered fresh-task test returned NULL,
below).

## What is not established

- **Out-of-sample convergence: NULL by pre-registered test.** e7 passed
  both pre-registered conditions; e8 failed the marker condition
  (treatment converged the means but diverged the constructs). The
  convergence claim is in-sample only. The e8 divergence is recorded as an
  observation — the node lists valid answers without deciding between them
  (`docs/UNDERDETERMINED_NODES.md`).
- **Out-of-sample quality: 1 of 6 cells clean** (e4-Mistral +3.07). The
  corpus rule is unsupported out-of-sample; `review.*` demonstrates no
  effect.

## The instrument

The measurement was corrected three times, two of which reversed a result;
every number in this summary is scored with the repaired instrument,
before/after recorded.

## The narrow shape of the record

Supported: the knowledge pack converges and improves output in-sample on
both providers, with a trustworthy placebo control. Not supported: any
generalisation — out-of-sample convergence (pre-registered NULL),
out-of-sample quality (1 of 6), the corpus rule, `review.*`. The record
stands as measured.
