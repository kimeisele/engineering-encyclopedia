# Why e1 is the exception

Item 2 of the follow-up. The honest exception in the convergence analysis:
the gap collapses (1.20 → 0.00), but within-run variance rises on both
providers, criterion disagreement stays 2/6, the structural markers do not
converge, and the placebo beats treatment on two of the four numbers.
Evidence only, no new hypothesis fitted to it.

## What the completions show

**e1's control failures were provider-orthogonal.** DeepSeek's control
characteristically fails `no_timestamp_key` (3/5 runs — it derives the
operation identity from a timestamp); Mistral's control never names an
identity at all (`operation_identity` fails 5/5) and has no dedup record
(`dedup_record` 5/5). The two providers failed *different* criteria in
control, which is the 2/6 modal disagreement.

**Treatment converges the means but not the criteria.** Both providers
reach mean 4.80 and both produce perfect runs (DeepSeek run-1/5 = 6/6,
Mistral run-2/5 = 6/6) — the pack does produce complete idempotent
implementations on both. But each provider keeps its *own* residual
failure: DeepSeek still fails `no_timestamp_key` in 2/5 treatment runs
(run-2, run-3 — timestamp-derived keys), Mistral still fails
`effect_guarded_by_record` in 3/5 (no transaction/unique guard). Different
residuals on different providers keep the modal disagreement at 2/6, and
the run sets split into full (6/6) and partial (3–4/6) implementations —
which is why within-run variance doubles on both providers
(DS 1.00 → 1.30, MR 0.84 → 1.30).

**The placebo's 0/6 agreement is agreement on absence.** Both providers'
placebo runs fail the same four criteria (`dedup_record`,
`check_before_effect`, `effect_guarded_by_record`, `durable_record` in 4/5
runs): the irrelevant pack yields uniformly minimal, non-idempotent
workers (scores 2–4, low sd). Modal agreement achieved by both providers
failing the same construct is not the convergence the claim is about —
and on the between-provider gap the treatment (0.00) still beats the
placebo (0.20). (This corrects the earlier convergence note: the placebo
beats treatment on disagreements and marker overlap, not on the gap.)

## What is different about e1, and its limit

e1 is the only in-sample task whose control failures are
provider-orthogonal and whose rubric contains a criterion the pack does
not reliably move on either provider — DeepSeek's residual is the
timestamp-derived key, Mistral's is the missing atomic guard, and the
treatment lifts each provider where it was weak without closing the other's
gap, so the runs scatter. That is a description of the completions. Why
the pack fixed Mistral's missing identity but not DeepSeek's timestamp key,
and fixed DeepSeek's guard but not Mistral's, is **unexplained** — and
that is the honest residual.
