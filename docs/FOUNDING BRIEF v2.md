# Founding Brief v2.0 — Engineering Encyclopedia

**Status:** final, one-shot implementation order.
**Leading question this project must answer:** *What is the minimal architecture that demonstrates whether versioned engineering knowledge nodes measurably improve the behaviour of coding agents?*

---

## 0. Thesis (read this before anything else)

Coding agents already contain the knowledge in this encyclopedia. They know what idempotency is. They know `shell=True` is dangerous. They fail anyway — not because the knowledge is absent, but because it is stored in weights: activated probabilistically, unevenly across contexts, impossible to inspect, impossible to patch, impossible to verify after the fact.

**This project does not teach agents new facts. It makes the application of known facts reliable and provable.**

Four properties follow, and every design decision in this document serves them:

1. **Reliable retrieval** — the knowledge arrives deterministically, not when the model happens to think of it.
2. **Inspectability** — a human can read exactly which node the agent relied on, and correct that node. A weight cannot be corrected.
3. **Consistency** — the same guidance across sessions, models and vendors. Swapping the model does not swap the knowledge.
4. **Anchoring against confabulation** — a fixed, hashed, versioned text against which plausible invention becomes visible.

**The product is therefore not the retrieval engine. The product is the Application Report** (Section 7): the mechanism by which an agent must name the node it applied, the question it answered, and where in the artifact it answered it. Retrieval is a means to that end. If the Application Report is not implemented, this project has not been built, regardless of what else works.

The thesis is falsifiable, and Section 8 falsifies or supports it in the same implementation step.

---

## 1. Scope

### Build

A local-first, offline, deterministic knowledge base of versioned YAML engineering nodes, a keyword retrieval layer, a bounded context pack composer, a machine-checkable application report format, and a three-case experiment that measures whether the pack changes agent output.

### Do not build (negative list — binding)

These are not deferred features to sketch. They must be **absent** from code, directories, interfaces, CLI flags, configuration and documentation of v1:

- LLM routers, intent interpreters, or any model call in the query path
- Embeddings, vector stores, RAG frameworks, graph databases
- Network access of any kind during `query`, `search`, `show`, `related`, `validate`
- Runtime dependencies other than PyYAML and the Python standard library
- Federation, synchronisation, package manifests, trust models, signatures
- Web servers, daemons, orchestration, multi-agent frameworks
- Scheduled workflows that create issues, stale-knowledge automation, Dependabot
- Empty placeholder files, directories or modules with no v1 caller
- Any node beyond the eight specified in Section 4

Adding anything from this list is a defect, not initiative.

### Runtime constraints

Python 3.12+. PyYAML is the only runtime dependency. `sqlite3`, `argparse`, `pathlib`, `dataclasses`, `enum`, `json`, `hashlib`, `unittest` from the standard library. Everything works offline after `pip install`.

---

## 2. Repository

- **Name:** `engineering-encyclopedia`
- **Description:** Versioned engineering knowledge nodes that make coding-agent reasoning inspectable and provable.
- **Visibility:** public unless the authenticated account requires otherwise
- **Default branch:** `main`
- **Topics:** `engineering`, `coding-agents`, `developer-tools`, `knowledge-base`, `python`, `yaml`

### Licensing (two licences, non-negotiable)

- **Code** (`src/`, `tests/`, `experiments/`): MIT. File: `LICENSE`.
- **Knowledge content** (`knowledge/`, `taxonomy/`): CC BY 4.0. File: `knowledge/LICENSE`.
- `README.md` states both explicitly.

### Governance (deliberately minimal)

Protect `main` with exactly: pull requests required, force pushes blocked, deletion blocked, required status check `validate`. Nothing else. No approval requirement (a solo owner cannot satisfy it), no rulesets, no security-feature checklist, no CODEOWNERS.

Record what was requested, what was applied and what the platform refused in `docs/REPOSITORY_PROTECTION.md`. Do not weaken protection silently to make a command succeed.

### Credentials

Discover the environment (`git --version`, `gh --version`, `gh auth status`, `gh api user`) before writing anything. Never print, log or persist a token. Do not create the repository inside an unrelated Git repository.

---

## 3. Node schema

One YAML file per node under `knowledge/<area>/<name>.yaml`. The example below is **the binding quality bar**: every one of the eight nodes must reach this depth. Depth beats count. An omitted optional field is acceptable; an invented one is a defect.

```yaml
id: reliability.idempotency
version: 1
title: Idempotency
kind: principle
status: established        # draft | reviewed | established | disputed | deprecated

summary: >
  An idempotent operation can be repeated for the same logical intent without
  producing unintended additional effects. Repetition is made safe by identity
  and recorded completion, not by hoping the operation runs only once.

intent_signals:            # 4-12 phrases, as a user would actually type them
  - must not run twice
  - duplicate processing
  - retry safely
  - the same event arrives again
  - charged the customer twice
  - resume after crash

applies_when:
  - an operation can be retried by a caller, a queue or an operator
  - delivery or invocation can occur more than once
  - execution may resume after interruption

does_not_apply_when:
  - the operation is a pure read with no side effects
  - the caller can guarantee exactly-once invocation end to end

does_not_imply:            # negative knowledge — the highest-value field
  - exactly-once delivery
  - absence of concurrency
  - transactional safety across systems
  - that a retry loop is now correct

questions:                 # 3-6 concrete, answerable, checkable
  - What value identifies one logical operation, and where does it come from?
  - Where is completion recorded, and is that record durable before the effect?
  - What state remains after a failure between effect and completion record?
  - Can two workers observe the same operation as not-yet-done simultaneously?

techniques:
  - idempotency keys derived from caller-supplied identity
  - deduplication records written in the same transaction as the effect
  - atomic state transitions guarded by a unique constraint
  - deterministic operation identifiers derived from input content

risks:
  - check-then-act races between the completion lookup and the effect
  - deduplication state that is not durable across process restart
  - keys derived from timestamps or request arrival order

tradeoffs:
  - technique: persistent deduplication table
    benefit: survives restart and multi-worker deployment
    cost: durable storage, retention policy, contention on the key
    choose_when: effects are externally visible or irreversible
  - technique: natural idempotency via full-state overwrite
    benefit: no extra state to maintain
    cost: only possible when the operation is a total assignment
    choose_when: the operation sets a value rather than incrementing one

relations:                 # targets MUST exist among the eight nodes
  related:
    - reliability.retry-semantics
  requires_consideration_of:
    - concurrency.race-conditions

contexts:
  languages: [any]
  project_types: [worker, cli, web-service, automation]
  lifecycle_stages: [design, implementation, review]

provenance:
  origin: curated
  rationale: >
    Distilled from recurring failure modes in retry and queue handling; the
    negative-knowledge entries record confusions observed in practice rather
    than claims taken from a cited source.
  created_at: 2026-08-01
  last_verified_at: 2026-08-01
  verification_interval_days: 1095

keywords: [idempotency, duplicate execution, retry, deduplication, exactly-once]
```

### Schema rules

- `id` is stable, lowercase, dot-namespaced, unique. `version` is an integer, incremented on any content change.
- **Content hash:** SHA-256 over the canonically serialised node (keys sorted, no comments), first 12 hex characters. Computed by the loader, never stored in the file.
- `provenance.origin` ∈ {`curated`, `documentation`, `standard`, `research`}. `curated` requires a non-empty `rationale`. A provenance field that says nothing is worse than none.
- Required fields: `id`, `version`, `title`, `kind`, `status`, `summary`, `intent_signals`, `applies_when`, `does_not_imply`, `questions`, `risks`, `provenance`, `keywords`.
- YAML is loaded with `yaml.safe_load` only. Imported YAML is data, never configuration, never executable.

### Hard limits (enforced by the validator, tested)

| Field | Limit |
|---|---|
| `summary` | ≤ 70 words |
| `intent_signals` | 4–12 entries |
| `questions` | 3–6 entries |
| `does_not_imply` | 2–6 entries |
| `techniques`, `risks` | ≤ 8 entries each |
| any single list entry | ≤ 25 words |
| whole node file | ≤ 500 words |

---

## 4. The eight nodes

Exactly these, no more, no fewer. No second list of future candidates appears anywhere in the repository.

1. `reliability.idempotency`
2. `reliability.retry-semantics`
3. `concurrency.race-conditions`
4. `python.files.atomic-replacement`
5. `python.processes.subprocess-safety`
6. `security.input-validation`
7. `testing.coverage-limitations`
8. `observability.error-context`

All `relations` targets must resolve within this set. A relation to a non-existent node fails validation. There is no `storage.*` namespace and no `risks.*` namespace; file-replacement knowledge lives in `python.files.atomic-replacement` only.

The taxonomy (`taxonomy/node-kinds.yaml`, `taxonomy/contexts.yaml`, `taxonomy/relation-types.yaml`) enumerates only values these eight nodes actually use.

---

## 5. Retrieval

**SQLite FTS5 is mandatory.** Build an in-memory FTS5 index over `title`, `summary`, `intent_signals`, `keywords`, `techniques`, `risks`, with BM25 ranking. Field weights: `intent_signals` 4.0, `keywords` 3.0, `title` 2.0, remainder 1.0.

**Fallback:** if the interpreter's `sqlite3` lacks FTS5, fall back to a pure-Python deterministic token-overlap scorer with the same field weights. The active path is reported in `trace.retrieval_backend`.

**Backend equivalence — outcome, not ranking.** BM25 and token overlap are different scoring methods; demanding identical rank order would only invite tuning the fallback to the ten regression queries. The binding criterion is therefore:

- for every regression query, both backends return **all required nodes** within the allowed primary-plus-supporting pack;
- no forbidden-to-dominate node ranks above all required nodes;
- exact ranking equality is **not** required and must not be asserted.

**Determinism is per backend.** Within a single backend, the same query, corpus and options produce byte-identical output; ties break by ascending `id`. A test runs each corpus query twice against each available backend and compares bytes. Determinism is never asserted *across* backends.

**Performance:** index build plus query completes in under 200 ms for the eight-node corpus on a cold start.

Model2Vec (~30 MB static embeddings, NumPy only) is a **candidate for a later, separate change**, mentioned here in one sentence and nowhere else. It is not installed, imported, referenced in `pyproject.toml`, or accommodated by an abstraction in v1.

---

## 6. Context pack

```yaml
request:
  original: "make sure this worker doesn't process the same job twice"
knowledge_revision: <sha256[:12] of the sorted corpus hashes>
context_pack_hash: 25f08ac04a91   # sha256[:12] over the canonical pack, this field excluded
retrieval_backend: fts5
context_pack:
  primary:                 # ≤ 3 nodes
    - id: reliability.idempotency
      version: 1
      hash: a3f1c9e04b72
      relevance: "identity and recorded completion for repeated jobs"
      questions: [...]
      does_not_imply: [...]
      risks: [...]
  supporting:              # ≤ 3 nodes, graph depth exactly 1 from primary
    - id: concurrency.race-conditions
      version: 1
      hash: 77b0e1d5aa38
      relevance: "two workers may observe the same job as unclaimed"
trace:
  selected: [reliability.idempotency, concurrency.race-conditions]
  excluded: [reliability.retry-semantics]     # ≤ 5 entries, ranked next
```

### Hard limits (enforced, tested)

| Limit | Value |
|---|---|
| primary nodes | ≤ 3 |
| supporting nodes | ≤ 3 |
| graph traversal depth | exactly 1 |
| `relevance` line | ≤ 15 words |
| `--detail compact` total | ≤ 150 words |
| `--detail guidance` total | ≤ 700 words |
| `--detail full` total | ≤ 2500 words |
| `trace.excluded` | ≤ 5 entries |

`context_pack_hash` is SHA-256 over the canonically serialised pack with the `context_pack_hash` field itself omitted, first 12 hex characters. It identifies *this* pack, and it is what binds an Application Report to the knowledge the agent was actually given.

Default detail level is `guidance`. Every emitted node carries `id`, `version` and `hash` at every detail level — this is what makes the Application Report checkable. Exceeding a limit truncates deterministically (lowest-ranked node first) and sets `trace.truncated: true`.

---

## 7. Application Report — the actual product

An agent that receives a context pack must return, alongside its work, a report in this form. This is what turns retrieval into evidence.

```yaml
application_report:
  knowledge_revision: 9c2b71ff04ad
  context_pack_hash: 25f08ac04a91      # must match the pack the agent received
  applied:
    - node: reliability.idempotency
      version: 1
      hash: a3f1c9e04b72
      questions_answered:
        - question: "What value identifies one logical operation?"
          answer: "The upstream job_id, carried through unchanged."
          location: "worker/consumer.py:41"
        - question: "Where is completion recorded, and is it durable before the effect?"
          answer: "Unique index on processed_jobs, inserted in the same transaction as the effect."
          location: "worker/consumer.py:58-73"
      unanswered:
        - question: "What state remains after failure between effect and record?"
          reason: "Single transaction, so the case cannot arise here."
  not_applied:
    - node: testing.coverage-limitations
      reason: "No test changes in this diff."
```

### Verification (`encyclopedia verify-report <report-path> --pack <pack-path>`)

Deterministic, offline, no model involved. **The verifier requires the original context pack.** A report alone cannot reveal that a node was silently dropped — the report only contains what the agent chose to mention, so an omitted node is invisible without the pack to compare against. `--pack` is mandatory, not optional.

**The context pack is part of the verification evidence and must be retained alongside the Application Report.** A report without its exact pack cannot later be fully verified.

The command checks:

**Binding to the pack**
- `context_pack_hash` in the report matches the hash recomputed from the supplied pack
- `knowledge_revision` in report and pack are identical
- every node in `context_pack.primary` and `context_pack.supporting` appears **exactly once** across `applied` and `not_applied` — omission fails, listing twice fails, listing under both dispositions fails
- the report contains **no node that was not in the pack**

**Binding to the corpus**
- every `node` exists in the corpus — an unknown ID is a hard failure
- every `version` and `hash` matches the current corpus — a mismatch means the agent cited stale or invented content

**Binding to the node content**
- every `question` string matches a question in that node **exactly**
- every question of an applied node appears in `questions_answered` or `unanswered` — silent omission fails
- every `answer` is non-empty and ≤ 40 words; every `location` is non-empty
- every `not_applied` entry carries a non-empty `reason`

Exit code 0 on pass, 1 on failure, with a machine-readable failure list. This command is the falsifier for "the agent actually used the knowledge", and it must exist and be tested even if no agent is ever wired to it in v1.

---

## 8. The three experiments — a first-class deliverable

Not documentation. Not a future phase. Delivered in the same step as the system.

Three tasks representing common and observable coding-agent failure patterns. How often they actually occur under these conditions is what the experiment measures — it is not assumed here:

| # | Task | Failure pattern | Node under test |
|---|---|---|---|
| E1 | "Write a worker that consumes jobs from a queue and charges a customer." | retry/redelivery without operation identity | `reliability.idempotency` |
| E2 | "Write a Python function that runs a git command with a user-supplied branch name." | `shell=True` with interpolated input | `python.processes.subprocess-safety` |
| E3 | "Write a function that updates a JSON config file on disk." | truncating write, no atomic replace | `python.files.atomic-replacement` |

### Method

For each task, two arms: **control** (task prompt only) and **treatment** (task prompt + context pack + the instruction to return an Application Report). Five runs per arm, ten runs per task, thirty runs total.

### Scoring

A deterministic Python rubric over the produced code — a checklist of observable properties, no model judging. Example for E2: is `shell=True` absent; is the argument passed as a list element; is the branch name validated or explicitly passed as data. Each criterion is a boolean; the score is the count. The rubric is fixed **before** the runs and lives in `experiments/rubrics/`.

### Deliverables

`experiments/README.md`, the three task prompts, the three rubrics, a runner that accepts recorded outputs as fixture files, and `experiments/RESULTS.md` with a per-task control-vs-treatment table.

If model execution is unavailable, ship the complete harness **without empirical results** and record the reason in `RESULTS.md`. Recorded fixtures may be included only when they are genuine outputs of an identified external agent run, with the model and date noted. **Never hand-author synthetic fixtures and present them as experiment observations.** An empty results table with an honest reason is a valid delivery; a fabricated one destroys the only evidence this project rests on. What is never acceptable is omitting the harness or replacing it with a claim of expected benefit.

The honest possible outcome is that the treatment arm does not improve. Record it. That result is worth more than the repository.

---

## 9. CLI

```
encyclopedia validate
encyclopedia list
encyclopedia show <node-id>
encyclopedia search "<text>"
encyclopedia related <node-id>
encyclopedia query "<request>"
encyclopedia verify-report <report-path> --pack <pack-path>
```

Options: `--format yaml|json` (default yaml), `--detail compact|guidance|full` (default guidance), `--max-primary N` (default 3, cap 3), `--max-supporting N` (default 3, cap 3), `--language`, `--project-type`.

No other commands. No `--no-router`, no router flags of any kind.

---

## 10. Tests and CI

`python -m unittest discover`. No pytest, no coverage tooling, no linters as required checks.

Required assertions:

- all eight nodes load and validate (the count is asserted; a short corpus fails the test rather than lowering the expectation)
- no duplicate IDs; all relation targets resolve; all taxonomy values known
- every schema limit in Section 3 holds for every node
- every pack limit in Section 6 holds for every corpus query
- byte-identical output on repeated identical queries **within each retrieval backend**
- backend equivalence per Section 5: both backends place all required nodes inside the pack and never let a forbidden-to-dominate node outrank all required nodes — ranking equality across backends is not asserted
- no node ID appears in any pack that is not in the corpus
- `verify-report` rejects, each as its own test: unknown node ID, wrong version, wrong content hash, altered question text, omitted question, **omitted pack node, report node absent from the pack, wrong `context_pack_hash`, mismatched `knowledge_revision`, duplicated disposition of the same node, node listed under both `applied` and `not_applied`**
- `verify-report` accepts a well-formed report against its matching pack (positive case)
- a regression corpus of **10 vague queries** in `evaluations/queries.yaml`, each with required and forbidden-to-dominate node IDs

CI workflow `validate.yml` runs on push and pull request: `python -m compileall src`, `python -m unittest discover`, `encyclopedia validate`, `encyclopedia query "..." --format json`.

The regression corpus is a guard against regressions, not evidence of quality. Section 8 carries the evidence. Say so in the file.

---

## 11. Delivery

1. Inspect environment and authentication.
2. Create the remote repository; clone; confirm the working directory is the repository root.
3. Bootstrap commit on `main`: README, both licences, `.gitignore`, `pyproject.toml`, `AGENTS.md`, **and `.github/workflows/validate.yml`**.
4. Push the bootstrap commit and let the workflow run at least once, so GitHub registers the check name `validate`.
5. **Only then** apply the branch protection from Section 2, including `validate` as a required status check; record the outcome.
6. Open one issue describing this implementation.
7. Branch, implement, run all checks, push, open a **draft** pull request.
8. Do not merge. Leave the repository ready for review.

A required status check cannot reliably be configured before GitHub has observed the check at least once. Following this order avoids an improvised workaround and an avoidable deviation entry.

Final report must state: repository URL, local path, authenticated login, default branch, protections applied and refused, issue number, PR number, head commit SHA, checks executed, experiment status, known limitations. No credentials, ever.

---

## 12. Priority rule (binding under pressure)

If context, time or budget runs short, sacrifice in this order — **top first**:

1. Repository settings, protection, topics, templates
2. Documentation beyond README and REPOSITORY_PROTECTION
3. CLI convenience surface beyond `validate`, `query`, `verify-report`
4. The size of the regression corpus (down to a minimum of five queries)

**Never sacrifice, in any circumstance:**

- the depth and quality of every node that is delivered (Section 3 bar)
- the Application Report and `verify-report` (Section 7)
- the three experiment harnesses and their rubrics (Section 8)
- determinism and the hard numeric limits

**The corpus is not a pressure valve.** Reduce secondary documentation and CLI convenience before touching the eight nodes. If fewer than eight can be completed at the required quality, **stop and deliver the completed nodes as an explicitly incomplete implementation** — recorded in `DEVIATIONS.md`, stated in the final report, and with the corpus test marked as failing rather than adjusted. Do not silently redefine the corpus to make the suite pass.

A partial delivery is permitted. A partial delivery that presents itself as specification-conformant is not. Eight shallow nodes with full governance and no experiment is a failure; five nodes at full depth with a working `verify-report`, an honest deviation entry and a red test is a usable starting point.

---

## 13. Deviation report (mandatory)

Create `DEVIATIONS.md`. Every point at which this brief was ambiguous, contradictory, impossible, or where a judgement call was made, gets an entry:

```markdown
### D1 — <one-line title>
Section: 6
Brief says: <quote or paraphrase>
Problem: <why it could not be followed literally>
Decision: <what was done>
Alternative rejected: <and why>
Reversibility: easy | moderate | structural
```

Silent improvisation is the single most expensive failure mode in a one-shot build. An empty `DEVIATIONS.md` will be read as a failure to notice, not as a perfect specification.

---

## 14. Stop conditions

Stop and report rather than proceeding if:

- a backend fails the equivalence criterion in Section 5 and the cause is not resolvable
- a node cannot reach the Section 3 quality bar without inventing provenance — deliver fewer nodes, never shallower ones
- the experiment cannot be scored deterministically for one of the three tasks
- following any instruction here would require a dependency beyond PyYAML

In each case: implement what is possible, record it in `DEVIATIONS.md`, and say so plainly in the final report. An honest partial delivery is more useful than a complete-looking one.

---

## 15. Decision rule

Every section of this repository must serve one of: node quality, the citation mechanism, provability, the experiment, or reproducibility. If something serves none of them, it does not belong in v1 — no matter how conventional it looks.

Build a small, real, inspectable core that can grow without being replaced. Do not build architecture on speculation.
