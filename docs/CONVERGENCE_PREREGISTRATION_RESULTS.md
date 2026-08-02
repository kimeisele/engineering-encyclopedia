# Pre-registered convergence test — results

Reported against the pre-registered markers and decision rule only
(`docs/CONVERGENCE_PREREGISTRATION.md`, committed ahead of the run,
`24542a8`). 120 completions (2 tasks × 3 arms × 2 providers × 10), 0
failures. No post-hoc markers are used in the decision; a clearly-labelled
post-hoc paragraph follows.

## Pre-registered metrics per task per arm

**e7 (concurrency.locking-strategy):**

| Arm | Between-provider gap | Marker-diff (mean \|rate_DS − rate_MR\|) |
|---|---|---|
| control | 0.30 (DS 5.80 / MR 5.50) | 0.10 |
| treatment | **0.10** (DS 5.00 / MR 4.90) | **0.03** |
| placebo | 0.80 | 0.17 |

**e8 (performance.cache-invalidation):**

| Arm | Between-provider gap | Marker-diff |
|---|---|---|
| control | 1.00 (DS 4.20 / MR 3.20) | 0.10 |
| treatment | 0.60 (DS 4.00 / MR 3.40) | **0.38** |
| placebo | 0.10 | 0.02 |

Marker detail, e8 treatment (where the decision turns):
- `cache_key_includes_version`: DS 5/10, MR 0/10 (control 1/10, 0/10) —
  DeepSeek adopted the version-in-key construct, Mistral did not.
- `ttl_or_expiry`: DS 7/10, MR 1/10 (control 10/10, 10/10) — DeepSeek
  kept TTL, Mistral dropped it.

## Verdict against the pre-registered decision rule

The rule: convergence generalises iff on BOTH tasks, treatment gap <
control gap AND treatment marker-diff < control marker-diff. **e7 passes
both conditions; e8 fails the marker-diff condition (0.10 → 0.38).** Per
the pre-registered rule, a failure on either task is a null: **the
convergence claim does not generalise.** On e8, treatment converged the
mean scores (gap 1.00 → 0.60) while *diverging* the constructs — DeepSeek
moved toward a version-in-key cache while Mistral dropped its TTL. The
null is stated exactly as the rule defined it, not softened.

## Post-hoc observations (clearly labelled, NOT part of the decision)

- On e7 the control was already near-converged (gap 0.30), so its pass is
  modest evidence — the treatment reduced a small gap to a smaller one.
- On e8 the placebo achieved gap 0.10 / marker-diff 0.02 — better than
  treatment on both numbers — but by absence-agreement: both providers
  lack the version-in-key construct (0/10 each) and share a plain TTL. This
  is the same agreement-on-absence pattern seen in e1's placebo, not
  construct convergence; the pre-registered rule did not weight it, and the
  claim is nulled by e8's marker-diff increase regardless.
- No post-hoc markers were added; the marker set and its regexes are exactly
  the pre-registered ones.
