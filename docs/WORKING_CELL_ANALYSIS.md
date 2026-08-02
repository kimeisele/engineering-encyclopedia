# What distinguishes the one working cell

Item 1 of the closing phase. Both predictors are dead (the corpus rule; the
baseline-headroom hypothesis — falsified by E6-Mistral having the lowest
unaided baseline and showing no effect). No third hypothesis is proposed
from theory. This is a concrete, evidence-only description of what the pack
did in the working cell (e4-Mistral) that it did not do in the failing
cells (e5 both providers; E6 both providers).

## The working cell: e4-Mistral

The pack's content became the artifact, verbatim, and was entirely absent
unaided.

Treatment run-1 (score 6/6):
```
class CircuitBreaker:
    def __init__(self, max_failures: int = 5, reset_timeout: float = 30.0):
        ...
        self.state = "closed"  # closed, open, half-open
    def call(self, func: Callable, *args, **kwargs):
        if self.state == "open":
            ... raise Exception("Circuit breaker is open")
```
Control run-1 (score 2/6), the unaided answer:
```
def call_downstream_api(
    url, method = "GET", ..., max_retries: int = 5,
    initial_backoff: float = 1.0, max_backoff: float = 30.0,
    backoff_multiplier: float = 2.0, ...
```
The unaided artifact contains **no circuit state, no threshold, no
fail-fast, no reset** — it answers "don't hammer it while it's down" with
retry-with-backoff. The pack supplied a construct (a three-state machine
with a threshold, a fail-fast raise and a half-open probe) that the model
had not produced in any form, and the rubric measures exactly that
construct.

## The failing cells

**e5 (both providers): the pack's construct was already in the unaided
artifact.** Mistral control run-1 (no pack) already contains
`def generate_correlation_id()`, `def log_error(correlation_id: str, ...)`
and `'correlation_id': correlation_id` — the correlation-id the pack
teaches is present without it. Control means 5.07 (DeepSeek) / 5.33
(Mistral) on criteria the pack targets. The pack added nothing the metric
could see, because the metric could already see the construct.

**E6 (both providers): the pack's questions were echoed in prose, but the
measured output did not move.** Mistral treatment run-1 names the claims
with locations ("... at worker.py:5", "... at worker.py:15"), but its
resolvable-location count is 2, identical to control (2.00): the unaided
control already cites the same two diff-locatable claims. The pack changed
the review's phrasing, not the number of resolvable locations. (The E6
measurement was itself repaired in the audit — `docs/OOS_E6_AUDIT.md` —
and the null survived.)

## The description, and its limit

Concretely: in the working cell the pack's content **entered the artifact
as a construct that was absent from the unaided output, and the metric
measures that construct**; in e5 the construct was already present unaided;
in E6 the pack's effect stayed in prose that the metric does not count.

That is a description, not a predictor, and it is not offered as a third
hypothesis. The data does not establish what would have predicted the
working cell: a weak unaided baseline did not (E6-Mistral was lower and
failed), and "the construct was absent unaided" is the same shape as the
dead baseline-headroom framing. The observable difference is reported
above; beyond it, the working cell is **unexplained** — and that is the
honest residual.
