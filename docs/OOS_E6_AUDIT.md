# E6 measurement audit

Item 1 of the follow-up. Before E6's null result could be interpreted as a
knowledge finding, the measurement itself had to be audited — the same
class of problem that produced the E5 negative cell. The flat 2.00
resolvable-location count in every arm, out of a "possible six", was the
suspicious pattern.

## 1. Do the reviews name file and line at all? Does the parser see it?

Yes, they name locations, and the parser missed one common format. Across
all 30 completions: `worker.py:N` citations in 29, singular "line N" in 13,
**plural "lines N-M" in 5** — and the parser only recognised `worker.py:N`
and singular "line N". Examples of the missed form:
- DeepSeek treatment run-2: "the diff lines 15-19 show a single for loop"
- DeepSeek placebo run-1: "The diff shows worker.py lines 1-22" and
  "Line 5 is `return result` inside `process()`"

Repair: the parser now accepts `lines?\s+(\d+)` (the range start).
Effect on the counts: DeepSeek control 2.00 → 2.20, DeepSeek treatment
2.40 → 2.40, **DeepSeek placebo 3.60 → 4.20**; Mistral unchanged
(2.00/2.00/1.60). The placebo, whose verbose style uses "lines N-M"
liberally, gains the most — the count rewards citing more lines, not
better findings.

## 2. What is the theoretical maximum of the location count?

Two of the three report claims are diff-locatable (claim 1 cites
worker.py:5, claim 2 cites worker.py:15); claim 3 ("the test run completed
without errors") is contradicted by the **raw output**, not by a diff line,
so a correct review of it has no diff location to cite. **The meaningful
maximum resolvable count is therefore 2, and control already sits at 2.00 —
the flat 2.00 was the arithmetic ceiling, not a knowledge signal.** (The
maximum over arbitrary cited lines is 22, which is why the placebo's
4.20 is possible; that count measures verbosity, not correctness.)

## 3. Audit of the six rubric criteria

Same class of defect as the earlier rubrics — and found:

- **`order_parts_addressed` fired 0/30 times.** The pattern was
  `(unaddressed|not addressed|not covered|no part of the order)`; the
  completions say "not supported"/"unsupported" (17 of 30 contain it), the
  natural phrasing for this task. A criterion designed for this task never
  fired — dead weight, identical to the `id_in_logs` class of defect.
  Repair: added `not supported|unsupported`. Effect: DeepSeek control
  3.00 → 3.80, treatment 3.20 → 3.40, placebo 3.60 → 4.40; Mistral control
  2.40 → 2.80, treatment 3.20 → 3.60, placebo 3.00 → 3.80.
- **`alternatives_excluded` fired 0/30 times** — the task does not invite
  alternative explanations; the criterion is task-mismatched (documented,
  left as-is: it belongs to the node's question set, not this task's
  materials).
- **Three criteria are saturated** at 5/5 in almost every cell:
  `claims_located`, `raw_output_cited`, `no_attitude_only` — they
  discriminate almost nothing in this task.
- `contradictions_checked` is the only criterion with real spread
  (0–3/5), and it is the one that behaves.

So the E6 rubric as shipped was: two dead criteria, three saturated, one
discriminating — a largely insensitive instrument, exactly what the flat
pattern suggested.

## 4. Before/after, against the surviving numbers

| Provider | Arm | Rubric before → after | Locs before → after |
|---|---|---|---|
| DeepSeek | control | 3.00 → 3.80 | 2.00 → 2.20 |
| DeepSeek | treatment | 3.20 → 3.40 | 2.40 → 2.40 |
| DeepSeek | placebo | 3.60 → 4.40 | 3.60 → 4.20 |
| Mistral | control | 2.40 → 2.80 | 2.00 → 2.00 |
| Mistral | treatment | 3.20 → 3.60 | 2.00 → 2.00 |
| Mistral | placebo | 3.00 → 3.80 | 1.60 → 1.60 |

**The null survives the repair.** After fixing the parser and the dead
criterion, the treatment still beats control on neither metric, and the
placebo outscored the treatment on DeepSeek (rubric 4.40 vs 3.40,
locations 4.20 vs 2.40) and on Mistral's rubric (3.80 vs 3.60). This is
the **third instrument defect the project has caught** (after the E2
`id_in_logs`/report-contamination and the e3 `no_direct_truncate`
repairs) — but unlike the first two, this repair does not reverse the
result; it confirms it. The E6 null is a measurement-confirmed finding.
