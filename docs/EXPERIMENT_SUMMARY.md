# Experimental programme — honest summary

One page, no advocacy. Full numbers in `experiments/RESULTS.md`; the
corpus-rule status in `docs/CORPUS_RULE.md`.

## The narrow result, first

**Of six out-of-sample cells (e4/e5 at n=15 on two providers, plus E6 on
two providers), exactly one shows a clean knowledge effect: e4-Mistral
(+3.07 vs pooled sd 1.01, placebo below control).** The claim the user
framed — "it is the cell whose unaided baseline was weakest" — is almost
right and is corrected with data: e4-Mistral's unaided baseline (control
2.80) is the second-lowest; the *lowest* baseline cell, E6-Mistral (2.40),
showed no effect at all. So the clean cell had a weak baseline, but a weak
baseline did not predict the effect. One clean cell out of six cannot carry
a rule.

## What was measured

A local knowledge base of versioned YAML nodes; a retrieval layer (FTS5 /
token-overlap) composing a context pack per request; a three-arm protocol
(control / treatment / placebo, n=5 per arm in-sample, n=15 out-of-sample)
run on two providers (DeepSeek, Mistral) through a provider-agnostic
harness; deterministic rubrics scored by the rubric's own regression suite.
Tasks: e1–e3 (written alongside the nodes they test), then e4/e5 (fresh
tasks on later nodes) and E6 (the first node whose own output is
machine-checkable). The measurement was repaired twice during the
programme.

## What held

- **In-sample, the effect held:** on e1–e3, treatment exceeded control on
  all six provider×task cells, and the placebo sat at or below control on
  five of six (one small anomaly, attenuated by repair).
- **The placebo design works:** a structurally identical pack with
  irrelevant content reliably separates prompt-structure effects from
  knowledge effects.

## What did not hold

- **Out-of-sample, the effect does not generalise:** of six cells, one
  clean (e4-Mistral), one ceiling-flat (e4-DeepSeek), two inside spread at
  n=15 (e5 both providers), two null (E6 both providers — the placebo
  outscored the treatment on DeepSeek and on Mistral's rubric).
- **The corpus rule (decision vs idiom) is unsupported out-of-sample** and
  retained only as a hypothesis. The baseline-headroom alternative is also
  weak: the clean cell had a low baseline, but the lowest-baseline cell
  showed nothing.
- **`review.*` (node 16) does not demonstrate an effect**, even after the
  E6 measurement was audited and repaired.

## The instrument

The project's strongest asset is its measurement discipline: it caught
**three defects in its own instrument** — the Application Report
contaminating the scored artifact (E2), a pattern crediting the wrong
construct (`no_direct_truncate` / `str.replace`, and `id_in_logs` matching
a method definition), and the E6 parser missing plural line ranges plus a
criterion that never fired. The first two reversed results; the third
confirmed the E6 null. Every number in this summary is scored with the
repaired instrument, before/after recorded.

## Bottom line

Supported: the knowledge pack changes agent output in-sample on both
providers, and the placebo control makes that measurement trustworthy.
Not supported: generalisation — one clean out-of-sample cell out of six, on
one node, on one provider, whose weak baseline did not predict it. The
corpus rule and the `review.*` namespace are hypotheses that this data
does not support.
