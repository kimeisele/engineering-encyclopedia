# engineering-encyclopedia

Versioned engineering knowledge nodes that make coding-agent reasoning
inspectable and provable.

Coding agents already contain the knowledge in this encyclopedia. They fail
anyway — not because the knowledge is absent, but because it is stored in
weights: activated probabilistically, unevenly across contexts, impossible to
inspect, impossible to patch, impossible to verify after the fact.

**This project does not teach agents new facts. It makes the application of
known facts reliable and provable.**

Four properties follow, and every design decision in this repository serves
them:

1. **Reliable retrieval** — the knowledge arrives deterministically, not when
   the model happens to think of it.
2. **Inspectability** — a human can read exactly which node the agent relied
   on, and correct that node. A weight cannot be corrected.
3. **Consistency** — the same guidance across sessions, models and vendors.
   Swapping the model does not swap the knowledge.
4. **Anchoring against confabulation** — a fixed, hashed, versioned text
   against which plausible invention becomes visible.

The product is the **Application Report**: the mechanism by which an agent
names the node it applied, the question it answered, and where in the artifact
it answered it. Retrieval is a means to that end.

## Measured result

The thesis is now supported by measurement, not just argument. A three-arm
experiment (control / treatment / placebo, n=5 per arm, two providers, final
scoring pipeline) measured whether the knowledge pack changes agent output:

| Task | DeepSeek (C / T / P) | Mistral (C / T / P) |
|---|---|---|
| e1 idempotency | 3.80 / 4.80 / 2.20 | 2.80 / 4.60 / 2.40 |
| e2 subprocess-safety | 3.60 / 5.00 / 2.80 | 3.60 / 5.00 / 4.80 |
| e3 atomic-replacement | 5.60 / 6.00 / 5.20 | 1.40 / 5.80 / 1.40 |

The placebo arm (a structurally identical pack with irrelevant content)
matches control — or scores below it — on five of six task×provider cells,
so the effect is not prompt length; on one cell (Mistral e2) the placebo
sits at the treatment level, so a structural component cannot be ruled out
there. An out-of-sample check on two later nodes (circuit-breaker,
correlation-id), scored with the repaired instrument, supports **one clear
out-of-sample effect** (e4-Mistral +3.20, placebo at control), one
ceiling-limited flat cell (e4-DeepSeek), and **two cells too small to call**
(e5-DeepSeek 0.00, e5-Mistral +0.27 — both inside within-arm spread even at
n=15 per out-of-sample arm; see `experiments/RESULTS.md`,
`docs/OOS_DIAGNOSIS.md`). Honest bounds: n=5 per arm in-sample, n=15 per
arm out-of-sample, three in-sample and two out-of-sample tasks, two
providers, one in-sample anomaly. The knowledge is **supported** by the
in-sample result, never claimed as proven; **out of sample the corpus rule
is not supported** — the only clean effect is a single cell (e4-Mistral,
on one provider, on one node), which cannot carry a rule, so the rule is
retained as an unsupported hypothesis. Full detail, raw scores and
caveats: `experiments/RESULTS.md`.

## Repository layout

```
src/encyclopedia/    code (MIT)
knowledge/           versioned YAML engineering nodes (CC BY 4.0)
taxonomy/            enumerations the nodes may use (CC BY 4.0)
evaluations/         regression queries with required / forbidden nodes
experiments/         three-case experiment harness (rubrics, prompts, runner)
tests/               unittest suite
docs/                founding brief, repository protection record
```

## Install

Requires Python 3.12+. The only runtime dependency is PyYAML; everything else
is the Python standard library. Everything works offline after install.

```sh
pip install .
```

## Usage

```sh
encyclopedia validate                          # validate corpus + taxonomy
encyclopedia list                              # all nodes
encyclopedia show reliability.idempotency      # one node, full detail
encyclopedia search "duplicate processing"     # ranked keyword search
encyclopedia related reliability.idempotency   # graph neighbours
encyclopedia query "make sure this worker doesn't process the same job twice"
encyclopedia verify-report report.yaml --pack pack.yaml
```

Options: `--format yaml|json` (default yaml),
`--detail compact|guidance|full` (default guidance),
`--max-primary N` (default 3, cap 3), `--max-supporting N` (default 3, cap 3),
`--language`, `--project-type`.

`query` emits a context pack with a deterministic `context_pack_hash` that
binds the pack to its content. `verify-report` checks an Application Report
against the exact pack the agent received — offline, no model involved.

## Licensing

- **Code** (`src/`, `tests/`, `experiments/`): MIT — see `LICENSE`.
- **Knowledge content** (`knowledge/`, `taxonomy/`): CC BY 4.0 — see
  `knowledge/LICENSE`.

## Governance

`main` is protected: pull requests required, force pushes blocked, deletion
blocked, required status check `validate`. See `docs/REPOSITORY_PROTECTION.md`.

## Experiments status

The three-case experiment harness (Section 8 of the founding brief) is
delivered: three task prompts, three deterministic rubrics, and a
provider-agnostic runner. Results are recorded in `experiments/RESULTS.md`;
see `experiments/README.md` for how the 30 completions are run and recorded.

## Status

Implementation of the founding brief, v1 — open for review as a draft pull
request. Deviations and judgement calls are recorded in `DEVIATIONS.md`.
