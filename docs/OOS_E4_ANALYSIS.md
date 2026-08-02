# Why e4-Mistral works — and what that implies for the rule

Item 2 of the follow-up. The one out-of-sample cell that survives n=15:
e4-Mistral, treatment +3.07 (pooled sd 1.01), placebo −0.47 below control.
Control is 2.80 while DeepSeek's control on the same task is 5.40. What
does Mistral get wrong without the node that DeepSeek gets right by itself?

## One paragraph (evidence-backed)

On e4, Mistral's unaided baseline substitutes retry semantics for
circuit-breaking: its control completions are functions titled "Calls a
downstream HTTP API with exponential backoff retry logic" with
`max_retries: int = 5` and `backoff_multiplier: float = 2.0` — they contain
**no circuit state, no failure threshold that opens a circuit, no fail-fast
while open and no success reset** (score 2/6; the rubric's `breaker_state`,
`failure_threshold`, `fail_fast_when_open` and `success_resets` all fail),
so Mistral answers "don't hammer it while it's down" with more retries.
DeepSeek's unaided baseline emits the complete pattern by itself:
`class CircuitState(Enum): CLOSED = ... OPEN = ... HALF_OPEN = ...`,
`failure_threshold: int = 5`, `recovery_timeout`, and a `_check_state()`
fail-fast guard (score 5–6/6 on the same rubric, unaided). The pack
therefore moved exactly the cell whose unaided baseline was weak, and the
completions **support** — they do not merely suggest — the
baseline-headroom hypothesis: the pack helps where the model's unaided
baseline is low (e4-Mistral control 2.80 → treatment 5.93) and produces no
measurable effect where the baseline already carries the concept
(e4-DeepSeek control 5.40; e5 controls 5.07/5.33 on both providers, whose
deltas remain inside spread at n=15). On this data the corpus rule
(decision vs idiom) is a worse predictor than baseline headroom.

## The candidate hypothesis, marked as tested, not assumed

The hypothesis stated in the instruction — "the pack helps only where the
model's unaided baseline is weak, and the corpus rule (decision vs idiom)
is a worse predictor than baseline headroom" — is **supported by the
completions** (above) but is itself only n=15 on four cells; it is a
hypothesis to test against E6 and any later task, not a finding on its own.
The two predictors are not mutually exclusive; the data simply does not
prefer decision-vs-idiom over baseline headroom.
