# DEVIATIONS

Every point at which the founding brief (`docs/FOUNDING BRIEF v2.md`) was
ambiguous, contradictory, impossible, or where a judgement call was made.
Silent improvisation is the single most expensive failure mode in a one-shot
build; an empty file would be read as a failure to notice, not as a perfect
specification.

---

### D1 — Repository creation: init-in-place instead of `git clone`
Section: 11
Brief says: "Create the remote repository; clone; confirm the working
directory is the repository root."
Problem: the working directory already contained `docs/FOUNDING BRIEF v2.md`
(and a `.DS_Store`); `git clone` refuses to clone into a non-empty directory.
Decision: created the empty remote with `gh repo create`, then
`git init -b main` in the existing directory, `git remote add origin`, and
push. End state is identical to a clone: working directory == repository
root, `origin` configured, `main` tracks `origin/main`.
Alternative rejected: cloning into a sibling directory and moving `.git` —
more moving parts, same end state, and the working directory the user opened
would still have had to absorb the files.
Reversibility: easy

### D2 — Retrieval backend on this machine (Section 5)
Section: 5
Brief says: "SQLite FTS5 is mandatory… if the interpreter's sqlite3 lacks
FTS5, fall back to a pure-Python deterministic token-overlap scorer."
Problem: none, but an initial environment probe wrongly reported FTS5
unavailable (a case-sensitive match against `pragma compile_options`, which
lists `ENABLE_FTS5`); the interpreter's sqlite3 (3.49.1) does support FTS5.
Decision: `fts5` is the active backend locally and in CI. The token-overlap
fallback is implemented, selectable with the `ENCYCLOPEDIA_BACKEND`
environment variable (test-only; no CLI flag), and both backends are run by
the test suite (determinism, equivalence, limits). The trace records the
active backend either way.
Alternative rejected: dropping the fallback — the brief mandates it.
Reversibility: easy

### D3 — Bootstrap commit carried a package seed and a smoke test (Sections 10–11)
Section: 10, 11
Brief says: bootstrap commit is "README, both licences, `.gitignore`,
`pyproject.toml`, `AGENTS.md`, and `.github/workflows/validate.yml`", and the
negative list forbids "empty placeholder files, directories or modules with
no v1 caller".
Problem: the bootstrap `validate` workflow must pass at bootstrap so GitHub
registers the check, and the workflow runs `python -m compileall src` and
`python -m unittest discover`. `compileall src` needs `src` to exist, and
`unittest discover` exits 5 when no tests exist (observed twice: no tests,
then tests/ without a package marker).
Decision: the bootstrap commit includes `src/encyclopedia/__init__.py` (a
real module: docstring + `__version__`, both still used by the v1 package)
and `tests/test_smoke.py` (a real test asserting the package imports and the
repo layout), plus `tests/__init__.py` which puts `src/` on `sys.path` so the
required `python -m unittest discover` works from a clean checkout. These are
not dead modules: the seed is the v1 package's `__init__` and the smoke test
remains in the suite.
Alternative rejected: weakening the bootstrap workflow to skip `compileall` /
tests — that would register a check that does not compile or test anything.
Reversibility: easy

### D4 — Data-root resolution for an installed wheel (README: "works offline after pip install")
Section: 1, 2
Brief says: the corpus lives at `knowledge/` and `taxonomy/` in the
repository, with a CC BY 4.0 `knowledge/LICENSE`, and "everything works
offline after pip install".
Problem: once installed as a wheel, the package has no reliable package-
relative path to the repo-root corpus (site-packages has no `knowledge/`),
and duplicating the corpus inside the wheel would blur the MIT-code /
CC BY-knowledge license boundary.
Decision: the loader resolves the corpus root in this order:
`ENCYCLOPEDIA_ROOT` env var → package-relative path (source checkout /
tests) → current working directory (an installed wheel run from the repo
root) → a clear error naming both options. The corpus stays repo-bound and
single-copy; the license split is preserved.
Alternative rejected: vendoring the corpus as package data inside `src/` —
two canonical copies and a license-mixing hazard.
Reversibility: easy

### D5 — Experiment results deferred to the owner (Section 8)
Section: 8
Brief says: experiments are delivered in the same step as the system; if
model execution is unavailable, ship the complete harness without empirical
results and record the reason in `RESULTS.md`.
Problem: model execution is in fact available in this environment (a Claude
Code CLI is installed and authenticated), but the owner explicitly directed
that the harness be provider-agnostic (`ENCYCLOPEDIA_RUNNER`), that no vendor
name appear anywhere, and that the 30 completions be run by the owner against
their own provider.
Decision: the harness (prompts, frozen packs, rubrics, runner, manifest
bookkeeping) is complete and tested; `experiments/RESULTS.md` records an
empty table with the honest reason. No synthetic fixtures exist or may be
added.
Alternative rejected: running the installed CLI to fill results — that would
name a vendor in the repository and bypass the owner's explicit instruction.
Reversibility: easy

### D6 — `relevance` lines are machine-generated (Section 6)
Section: 6
Brief says: each pack node carries `relevance` ("identity and recorded
completion for repeated jobs" in the example) and the line is limited to 15
words, but no generation rule is specified.
Problem: a hand-authored relevance string would not be reproducible from the
corpus, breaking the per-backend byte-identical-output guarantee.
Decision: `relevance` is generated deterministically — the `intent_signals`
entry with the highest token overlap with the request, truncated to 15
words, else the summary prefix. Packs therefore reproduce byte-for-byte.
Alternative rejected: omitting relevance — the example requires it.
Reversibility: easy

### D7 — Detail-level field sets and word-budget scope (Section 6)
Section: 6
Brief says: detail levels `compact | guidance | full` with total word limits
(150 / 700 / 2500), `--detail` default `guidance`, and every node carries
`id`/`version`/`hash` at every level; the example pack shows `questions`,
`does_not_imply`, `risks` per node.
Problem: the brief does not fix which fields appear at each level, nor
whether the budget counts the whole emitted document or only the
`context_pack` section.
Decision: field sets are `compact` = id/version/hash + relevance + summary;
`guidance` = compact + questions + does_not_imply + risks; `full` = everything
(applies_when, does_not_apply_when, techniques, tradeoffs, contexts,
keywords, intent_signals, relations). The budget is applied to the whole
emitted document (conservative reading); exceeding it truncates
deterministically, lowest-ranked node first, setting `trace.truncated: true`.
Alternative rejected: counting only the `context_pack` section — a weaker
reading that the hard-limits tests could not enforce honestly.
Reversibility: easy

### D8 — Local pip cannot install to user site-packages (environment)
Section: 1
Brief says: "everything works offline after pip install".
Problem: this macOS Framework Python refuses user-site installs
("Operation not permitted: …/Library/Python/3.13"), and the global
site-packages is not writable.
Decision: local verification uses a project-local `.venv` (gitignored) with
`pip install .`; the installed wheel resolves the corpus via the D4 rule.
CI is unaffected (fresh runner, `pip install .`).
Alternative rejected: `sudo`/system installs — invasive and unnecessary.
Reversibility: easy

### D9 — `not_applied` entries are not hash-bound (Section 7)
Section: 7
Brief says: "every `version` and `hash` matches the current corpus — a
mismatch means the agent cited stale or invented content".
Problem: the brief's own example `not_applied` entry carries only `node` and
`reason`, and a not-applied citation asserts nothing about the node's
content; requiring version/hash there would make the brief's example report
fail verification.
Decision: `verify-report` checks `version` and `hash` against the corpus for
`applied` entries only. `not_applied` entries must carry a non-empty `reason`
and must be pack nodes, but are not hash-bound.
Alternative rejected: enforcing version/hash on both dispositions — stricter
than the brief's own example allows.
Reversibility: easy

### D10 — Corpus extended from eight to ten nodes (Sections 1 and 4)
Section: 1, 4
Brief says: the corpus is "exactly these, no more, no fewer" (eight nodes)
and "any node beyond the eight specified in Section 4" is a defect.
Problem: after the Section 8 experiment, the owner instructed two new nodes
at the Section 3 quality bar, selected by the decision-vs-idiom rule derived
from the results (`docs/CORPUS_RULE.md`).
Decision: added `reliability.outbox-pattern` and
`performance.cache-invalidation`, both decision-type nodes; the node-count
assertion was raised 8 -> 10 as an intentional corpus change (the test still
fails on a short corpus). The founding brief remains the historical v1
specification and is not edited. The experiment evidence — frozen packs,
treatment prompts and the fixture manifest — is pinned to the eight-node
corpus it ran against; `test_frozen_experiment_packs_match_corpus` now
recomposes against that pinned corpus, so edits to the eight experiment
nodes fail loudly and require conscious regeneration of the experiment
artifacts.
Alternative rejected: silently keeping the count assertion at 8 with ten
files on disk (a weakened test), or regenerating the frozen packs (which
would erase the hash evidence the recorded runs were made against).
Reversibility: easy (remove the two nodes and revert the count assertion)

### D11 — Node 11 `testing.evaluation-contamination` (Sections 1 and 4)
Section: 1, 4
Brief says: the corpus is exactly the eight nodes of Section 4, and any node
beyond them is a defect.
Problem: the E2 analysis of the Section 8 experiment exposed a contract
defect — the Application Report reproduces a node's questions verbatim, and
an artifact scored together with its own description is contaminated. The
owner instructed that this be written up as a node (it requires a design
decision: where the artifact ends and its description begins), per the
decision-vs-idiom corpus rule (`docs/CORPUS_RULE.md`).
Decision: added `testing.evaluation-contamination` as node 11 at the Section
3 quality bar and raised the count assertion 10 -> 11 as an intentional
corpus change. The founding brief remains the historical v1 specification.
Alternative rejected: leaving the finding only in `experiments/RESULTS.md` —
the brief exists precisely to make such findings retrievable and inspectable
(no second list of candidates; the node is delivered now, not deferred).
Reversibility: easy (remove the node and revert the count assertion)

### D12 — Nodes 12–15 chosen by the corpus rule (Sections 1 and 4)
Section: 1, 4
Brief says: the corpus is exactly the eight nodes of Section 4, and any node
beyond them is a defect.
Problem: after the placebo-controlled experiment supported the thesis, the
owner instructed four further nodes at the Section 3 bar, chosen by the
decision-vs-idiom corpus rule with three criteria (decision required;
failure a model plausibly makes despite knowing the concept; reachable by
relations from the corpus).
Decision: added `reliability.circuit-breaker`, `reliability.dead-letter-queue`,
`observability.correlation-id` and `concurrency.locking-strategy`, raising
the count assertion 11 -> 15 as an intentional corpus change. Each is
reachable from an existing node (retry-semantics ×2, error-context,
race-conditions) and none of the eleven existing nodes was modified. Two of
them (circuit-breaker, correlation-id) become out-of-sample experiment tasks.
The founding brief remains the historical v1 specification.
Alternative rejected: expanding the corpus without the three criteria — the
rule exists to gate exactly this.
Reversibility: easy (remove the four nodes and revert the count assertion)
