# Out-of-sample proposal — what the data implies

Item 3 of the follow-up. Proposal only; nothing is changed until the owner
decides.

## The honest conclusion

**The corpus rule in `docs/CORPUS_RULE.md` does not survive out-of-sample
testing as a predictor of experimental payoff.** The rule said decision-type
nodes pay off; four such nodes were added; two were tested out of sample and
the effect reproduced in one of four cells (e4-Mistral +3.20), was flat in
two (e4-DeepSeek, e5-DeepSeek) and negative in one (e5-Mistral −1.40). That
is a finding worth more than the nodes: the decision-vs-idiom distinction is
a necessary condition, not a sufficient one.

## Proposed decision: (c) — the corpus rule is incomplete

Exactly one of (a)/(b)/(c); the diagnosis rules out (a) (the correlation-id
node is sound and correctly matched) and (b) (retrieval returned the right
node as primary). So the proposal is **(c)**, with what the data supports
instead:

A node's experimental payoff depends on two further gates that the current
rule does not state, and the data supports adding them:

1. **Control-arm headroom.** The flat cells had little room: e4-DeepSeek
   control 5.40/6.00, e5-DeepSeek 4.80, e5-Mistral 5.20 — treatment cannot
   show an effect the control already has. The only clean positive cell
   (e4-Mistral) is also the only one with a low control (2.80). The rule
   should require: a candidate node is only testable when the control arm of
   its task has headroom.
2. **Rubric sensitivity.** The negative cell was largely a rubric blind spot
   (see `docs/OOS_DIAGNOSIS.md`: `log\w*\(` cannot match `logger.error(...)`
   and was satisfied by a method named `log_success`). A node whose
   recommended design the rubric cannot credit cannot be measured, so a
   candidate node is only testable when the rubric can see the design the
   node teaches. (This is the same family as node 11,
   `testing.evaluation-contamination`, applied to the rubric itself.)

If the owner accepts (c), the corpus rule gains the two gates and the
out-of-sample result is recorded as the evidence for them; no node is
removed, no rubric is changed in this step. If the owner prefers a stricter
reading — that a decision-type node that does not move its out-of-sample
delta fails the rule — that would imply revisiting whether any of the four
new nodes earns its place, which the diagnosis above does not support.
