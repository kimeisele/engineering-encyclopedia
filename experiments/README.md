# Experiments — three-case harness (Section 8 of the founding brief)

A first-class deliverable, not documentation. Three tasks representing
common, observable coding-agent failure patterns. The honest possible
outcome is that the treatment arm does not improve; that result is worth
more than the repository.

| # | Task | Failure pattern | Node under test |
|---|---|---|---|
| E1 | "Write a worker that consumes jobs from a queue and charges a customer." | retry/redelivery without operation identity | `reliability.idempotency` |
| E2 | "Write a Python function that runs a git command with a user-supplied branch name." | `shell=True` with interpolated input | `python.processes.subprocess-safety` |
| E3 | "Write a function that updates a JSON config file on disk." | truncating write, no atomic replace | `python.files.atomic-replacement` |

## Method

Two arms per task:

- **control** — the task prompt only (`experiments/tasks/<task>-control.txt`)
- **treatment** — the task prompt + a context pack + the instruction to
  return an Application Report (`experiments/tasks/<task>-treatment.txt`)

Five runs per arm, ten per task, thirty runs total. The treatment packs are
frozen in `experiments/packs/<task>.yaml`; they were produced with
`encyclopedia query "<task prompt>" --detail guidance` and are part of the
delivery so treatment reports can be verified later.

Scoring is a deterministic Python rubric over the produced code — a
checklist of observable boolean properties, no model judging. Rubrics live
in `experiments/rubrics/` and are fixed before the runs. The score is the
count of satisfied criteria.

## Provider-agnostic runner

The harness never names a vendor. The concrete model command comes from the
`ENCYCLOPEDIA_RUNNER` environment variable: a shell command that **reads the
prompt on stdin and writes the model's completion to stdout**. No vendor
name appears anywhere in code, config or docs.

```sh
export ENCYCLOPEDIA_RUNNER="your-provider-command"   # prompt on stdin, completion on stdout
python3 experiments/runner.py prompt e1 control      # see a prompt
python3 experiments/runner.py run e1 control out/e1-control-1.py
python3 experiments/runner.py score e2 out/e2-treatment-1.py
python3 experiments/runner.py summarize experiments/fixtures --out experiments/RESULTS.md
```

`run` writes the completion to the given file and appends one line to
`experiments/fixtures/manifest.jsonl` with the task, arm, output path, date,
the `ENCYCLOPEDIA_RUNNER` value and (for treatment) the pack hash — the
"identified external agent run, with model and date noted" record Section 8
requires.

## Network: what may and may not use it

**The Section 1 network ban applies to the query path only** — `encyclopedia
query`, `search`, `show`, `related`, `validate` and `verify-report` are
offline and must stay offline.

**The experiment harness may use the network** — the provider command behind
`ENCYCLOPEDIA_RUNNER` is free to reach its own API. These are deliberately
separate: retrieval stays deterministic and offline; the experiments measure
an external agent. Do not wire the two together — a future change that lets
`encyclopedia query` call a network provider would violate Section 1.

## Verifying treatment reports

Treatment outputs should contain an `application_report` (the pack is bound
by `context_pack_hash`). Verify a recorded report against its frozen pack:

```sh
encyclopedia verify-report out/e1-treatment-1-report.yaml --pack experiments/packs/e1.yaml
```

## Honesty rules

- Recorded fixtures may be included only when they are genuine outputs of an
  identified external agent run, with model and date noted.
- **Never hand-author synthetic fixtures and present them as experiment
  observations.** An empty results table with an honest reason is a valid
  delivery; a fabricated one destroys the only evidence this project rests
  on.
- `RESULTS.md` currently records that no completions have been run yet, and
  why. `summarize` regenerates it from the manifest when runs exist.
