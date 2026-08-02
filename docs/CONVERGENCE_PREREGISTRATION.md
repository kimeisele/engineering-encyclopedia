# Pre-registration — convergence out-of-sample test

Committed ahead of any run. The convergence claim (the pack makes output
the same shape across vendors and runs) needs the same out-of-sample test
the quality claim received. This file fixes, before seeing any completions:
the two tasks, the arms, the structural markers, the predicted direction
and the decision rule. Post-hoc markers may be reported later only
separately and clearly labelled.

## Tasks (nodes exist in the corpus; tasks NOT designed alongside them)

- **e7 — `concurrency.locking-strategy`** (node 15).
  Task: "Write a function that updates a shared counter. Two workers may
  update it at the same time; choose a locking or conflict-detection strategy
  so that no update is ever lost."
- **e8 — `performance.cache-invalidation`** (node 10).
  Task: "Write a function that returns a cached value for a key, and must
  not serve a stale value after the source data changes."

## Protocol

Three arms (control / treatment / placebo with `observability.error-context`
content), two providers (DeepSeek, Mistral), n=10 per cell. 120 completions
total (2 tasks × 3 arms × 2 providers × 10). Same pipeline as the previous
analysis (extraction + comment stripping for code tasks; extraction only
for e6-style prose — not applicable here). Rubrics for e7/e8 are fixed
before the runs (below, in `experiments/rubrics/`).

## Pre-registered structural markers (exact regexes)

Matched with `re.search` + `re.DOTALL` over the scored artifact.

**e7 (locking-strategy):**
- `atomic_guard` = `atomic|compare[- ]?and[- ]?swap|\bCAS\b|UPDATE .* SET|INSERT.*ON CONFLICT|insert or ignore|unique`
- `explicit_lock` = `Lock\(\)|RLock\(|mutex|acquire\(|release\(|with .*lock`
- `version_or_cas_field` = `version|updated_at|expected|WHERE [a-z_]+ =`
- `single_guarded_block` = `with .*lock:|with atomic|atomic\s*\(|CAS\s*\(`

**e8 (cache-invalidation):**
- `cache_key_includes_version` = `key\s*[=+].{0,40}(version|updated|fingerprint|mtime)|f["'][^"']*\{(version|updated|fingerprint|mtime)`
- `explicit_invalidation` = `invalidate|\.delete\(|\.pop\(|\.clear\(|del\s+\w+\[`
- `ttl_or_expiry` = `ttl|expir|max_age|deadline|time\.time|monotonic`
- `miss_refetch` = `(miss|not in cache|absent|KeyError).{0,60}(fetch|reload|compute|get)`

## Predicted direction (registered before any run)

For BOTH tasks, relative to control:
1. **treatment reduces the between-provider gap** in mean rubric score
   (|mean_DS − mean_MR|), and
2. **treatment reduces the marker-profile difference** (mean per-marker
   |rate_DS − rate_MR|) so that both providers contain the same constructs.
The **placebo** is predicted NOT to produce either reduction (it did not in
the in-sample convergence analysis).

## Decision rule (registered before any run)

The convergence claim **generalises** iff, on BOTH e7 and e8:
- treatment gap < control gap, AND
- treatment marker-difference < control marker-difference.
A failure on either task is a null for the claim (the claim is stated for
the corpus, not per node). Post-hoc markers, if any are added later, are
reported separately and labelled post-hoc.

## Fixed rubrics

`experiments/rubrics/e7_locking_strategy.yaml` and
`experiments/rubrics/e8_cache_invalidation.yaml` are committed with this
file, before any run.
