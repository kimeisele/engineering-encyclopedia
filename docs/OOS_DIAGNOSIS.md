# Out-of-sample diagnosis — Mistral E5 negative cell

Item 2 of the follow-up. The question: Mistral E5 (correlation-id),
treatment −1.40 against control (5.20 → 3.80). A pack that makes output
worse is a defect, not noise. Evidence below; nothing was changed.

## The three questions

**Did retrieval return the right node? Yes.** The e5 pack
(`experiments/packs/e5.yaml`) selects `observability.correlation-id` as
primary #1 for the task "Write an error handler for a two-service request so
an operator can trace one request across both services." The ranking is not
the problem.

**Did the node's questions pull the model toward a worse design, or merely
distract? Both, and the first is mostly a rubric artefact.** The control arm
writes header-based propagation with inline ids; the treatment arm writes
the node's own recommended design (its tradeoff endorses explicit
parameter-passing over middleware), which the e5 rubric cannot see:

- The rubric's `id_in_logs` pattern is `log\w*\([^)]*(request_id|correlation_id|trace_id)`.
  It cannot match the idiomatic `logger.error(...)` form, because the dot
  between `logger` and `error` breaks `log\w*\(`. It matched in the best
  control run by accident, on a method *definition* rather than a log call:
  `log_success(self, trace_id: str, response_time: float) -> None:` — the
  criterion credits a function named `log_success`, not logging. Meanwhile a
  treatment run that genuinely logs with the id fails it:
  `self.logger.error(error_message, extra=error_context)` (Mistral e5
  treatment run-1, score 4; its `id_in_logs` fails 5/5 treatment runs vs
  2/5 control).
- `id_propagated` and `downstream_reuses` only credit header-based
  propagation (`headers[...]`, `X-Request-Id`); the treatment's
  explicit-parameter design (`request: ServiceRequest` carrying
  `correlation_id`) is invisible to both.
- `errors_carry_id` only credits an inline same-line
  `(error|exception|raise)...correlation_id`; the treatment attaches the id
  via a context dict (`wrapped_error.__dict__.update(error_context)`), which
  does not match.

**Distraction is real and comes from the pack composition.** The e5 pack's
supporting nodes (`reliability.dead-letter-queue`, `reliability.circuit-breaker`)
are depth-1 neighbours of correlation-id, and the treatment model absorbed
them: Mistral e5 treatment run-5 (score 2) contains a whole
`handle_dead_letter` method whose context is the dead-letter node, and its
handler never demonstrates the two-service call flow at all — so part of the
deficit is genuine incompleteness, but the larger part is the rubric's
blindness to the design the node itself recommends.

## Is the node deficient, or correct but wrongly matched?

The node is correct and correctly matched. The deficiency is in the e5
measurement: its `id_in_logs` pattern cannot match real `logger.error(...)`
calls (and, worse, credits a method named `log_success`), and its
propagation criteria cannot see the explicit-parameter design the node's own
tradeoff endorses. This is the evaluation-contamination family again — the
rubric, not the node, is the blind spot — compounded by supporting nodes in
the pack distracting the model.
