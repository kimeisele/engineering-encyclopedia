# Underdetermined nodes — an observation about convergence

Item 1 of the closing phase. Recorded as an observation with evidence. **No
action is taken on it: no node is changed, no rule is created.** The
pre-registered e8 result is not a plain null and is not filed as one: the
treatment moved BOTH providers and moved them apart — that is an effect
without a shared direction.

## The e8 divergence

On `performance.cache-invalidation` (e8), the pre-registered test showed
DeepSeek adopting a version-in-key cache (0/10 → 5/10) while Mistral
dropped its TTL (7/10 → 1/10) and moved to an internal-version/invalidate
design. Same node, opposite directions. From the completions:

- DeepSeek treatment: "The cache key is a tuple of (user_key,
  source_version)" (run-2), "the cache key is (user_key, source_version)"
  (run-3, run-5) — the version-in-key answer.
- Mistral treatment: `self._version = 0`, `def invalidate(self, key)`,
  `cached_value, cached_version = self._cache.get(key, (None, -1))` (runs
  1–5) — the internal-version-and-invalidate answer, with **no**
  version-in-key (0/10).

## Does the node state a decision, or list options?

The node lists options. Its techniques are an option set — "cache keys
that include a source version or fingerprint", "explicit invalidation on
the write path", "TTL as a fallback" — and its tradeoffs present two valid
answers (TTL-only vs explicit-invalidation-on-writes) with conditional
`choose_when` guidance that the task does not resolve. Its questions are
decision-shaped ("What identifies a cached entry, and does it include the
source version?") but the node does not decide which answer holds for the
task; both providers picked valid answers, different ones. **The
divergence is explained by the node being underdetermined.**

## The contrast: e3 and e4, where convergence was strongest

- `python.files.atomic-replacement` (e3): its techniques ARE decisions —
  "write to a temp file, fsync, then os.replace" is a singular
  prescription, and the questions' answers ("Is the temp file created in
  the same directory?" → yes; "Is the data flushed before the rename?" →
  yes) are fixed by it. Both providers converged on temp+rename+fsync
  (100%/100%/100%).
- `reliability.circuit-breaker` (e4): its techniques ARE decisions —
  "count failures in a rolling window and open past a threshold", "a
  single half-open probe after a cooldown" — singular choices; both
  providers implemented the same state machine (markers 0.85 → 0.10).

**Those nodes decide where this one lists.** e3 and e4 prescribe a single
answer; e8 presents alternatives with conditions the task does not settle.

## The observation, recorded as such

Convergence may require the node to **decide, not merely to inform**: a
node that names a concern and lists valid answers leaves the choice to the
model, and different models choose differently — an effect without a
shared direction. This is a testable property of nodes (deciding vs
listing), recorded here as an observation with the evidence above. It is
not a rule, no node is changed, and nothing follows from it in this
programme.
