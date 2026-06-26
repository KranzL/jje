# Judge, Jury, Executioner (JJE)

A generator–critic loop for Claude Code. You ask for a change and seat a panel of
reviewers; JJE plans it, builds it on a throwaway branch, has independent
tool-backed jurors review it in parallel, and a Judge routes the result —
**revise, replan, accept, or escalate** — until it ships or hands back to you.
Nothing reaches `main` until the Judge accepts *and* CI is green.

It runs on portable Claude Code primitives only — subagents, skills, hooks — so
you can drop it into any repo. No SDK, no external service, no API keys beyond the
one Claude Code already uses.

## How it works in 60 seconds

```
/jje "add event_source to the bronze writer and surface it in silver"
```

1. **Planner** drafts steps, files-in-scope, and explicit success criteria.
2. You **seat the jury** — pick a preset (`quick`, `pipeline`, `full`, …) or
   choose jurors individually. This is your one entry point per cycle.
3. **Executor** builds the change on a scratch branch in an isolated git
   worktree — never on `main`.
4. The **jury** reviews the candidate in parallel. Each juror is independent
   (none sees another's verdict), scoped to one lane, and tool-backed where
   possible: security runs `gitleaks`/`semgrep`, correctness runs the test
   suite, cost runs `EXPLAIN`. Each emits one structured JSON verdict.
5. The **Judge** reads only the verdicts (it never re-reviews the code) and
   returns one route:
   - **REVISE** — fix the blocking findings, same jury re-runs.
   - **REPLAN** — the approach is wrong; back to the Planner, re-seat.
   - **ACCEPT** — no blockers → CI gate → commit.
   - **ESCALATE** — budget exhausted or a finding oscillates → hand to you.
6. Two counters guarantee termination: an **iteration budget** and an
   **oscillation guard** (a recurring blocking finding or a contradictory pair
   escalates instead of looping). A `PreToolUse` hook makes "nothing reaches
   `main` without ACCEPT + green CI" an enforced invariant, not a promise.

## Install (project-scoped, the canonical form)

Copy the `.claude/` directory and the `.jje/` config into the repo you want to
work in (or clone this repo and work inside it):

```sh
cp -r .claude /path/to/your/repo/
cp -r .jje    /path/to/your/repo/
cp /path/to/your/repo/.jje/config.example.json /path/to/your/repo/.jje/config.json
```

Then in that repo, run `/jje "<your request>"`.

Prerequisites: `python3`, `git`, and `jq` (the hooks use it). The jurors call
external tools (`gitleaks`, `semgrep`, `ruff`, `pytest`, `dbt`, …) when present
and gracefully skip — reporting the skip — when they're not. Install the ones
for your stack to get tool-backed review instead of model-only review.

> A plugin/marketplace distribution (`/plugin install jje@jje`) is staged in
> `.claude-plugin/` and `docs/PACKAGING.md`. The project-scoped layout above is
> the tested canonical artifact; the plugin form is the borrowable convenience.

## The juror roster

Each juror is a thin agent that preloads its review skill (the exact commands +
blocking bar) and emits one verdict. Add your own with three files — see
[CONTRIBUTING.md](CONTRIBUTING.md).

### Code lane

| Juror | Model | Reviews | Blocks on |
|---|---|---|---|
| `correctness-juror` | Sonnet | Logic, edge cases, complexity | Failing test, wrong output, unbounded complexity on a hot path |
| `security-juror` | Haiku | Injection, secrets, authz, deps | Committed secret, injection, known CVE, missing authz |
| `structure-juror` | Haiku | Naming, boundaries, conventions | Breaks the build or an agreed standard |
| `observability-juror` | Haiku | Logging, metrics, tracing, errors | New surface with no error handling / instrumentation |
| `interface-compat-juror` | Sonnet | Public API / signature stability | Breaking change to a published interface, no version bump |

### Data-pipeline lane

| Juror | Model | Reviews | Blocks on |
|---|---|---|---|
| `data-contract-juror` | Sonnet | Schema evolution, event contracts | Backwards-incompatible change with live consumers |
| `idempotency-juror` | Sonnet | Write semantics, dedup, watermarks | Non-idempotent write, duplicate risk, wrong MERGE key |
| `cost-juror` | Haiku | Scans, partitioning, file sizing | Full scan on a big table, unbounded fan-out |
| `data-quality-juror` | Haiku | Nulls, dedup, referential integrity | Failing data test, dropped quality constraint |
| `governance-juror` | Sonnet | Ownership, PII, catalog | Untagged PII, governed change with no owner |

### Presets

| Preset | Jurors |
|---|---|
| `quick` | correctness + security |
| `code-full` | all 5 code jurors |
| `pipeline` | data-contract + idempotency + data-quality + cost |
| `security-sweep` | security + governance + data-contract |
| `full` | all 10 |
| `custom` | choose individually |

## Configuration

Copy `.jje/config.example.json` to `.jje/config.json` and edit. Keys:

- `default_budget` (default `6`) — max Executor→Judge trips; CI-failure bounces
  count against it.
- `default_preset`, `protected_branches`, `ci_command`.
- `escalation_policy` — `stop` (default: hand the candidate + open findings to
  you and halt) or `ship-with-caveats`.
- `oscillation.repeat_threshold` (default `2`) and `oscillation.detect_contradictions`.
- `models` — per-role model overrides.
- `jurors` + `presets` — the roster registry and the named panels.

## Safety guarantees (and their honest limits)

- **Candidate never touches `main`.** The Executor works only in a scratch-branch
  worktree; while a run is active the `jje-ci-gate` hook blocks every
  commit/merge/push without a `.jje/COMMIT_APPROVED` marker, and pushes to a
  protected branch are denied outright.
- **The CI gate is real.** The marker is minted only after `jje_state.py ci`
  records a verifiable result artifact (the actual exit code) and `accept`
  validates exit 0 — not after the model says "CI passed".
- **Termination is capped independently of the model.** The loop-guard hook keeps
  its own Executor-spawn counter, so even an orchestrator that skips the state
  CLI cannot loop past the budget.
- **Limit:** the *step-by-step* orchestration is the main agent following a
  skill (probabilistic), backed by deterministic counters and hooks (hard). The
  guarantees above hold by construction; the loop's smooth running relies on the
  orchestrator following the skill.

## Layout

```
.claude/
  agents/            planner, executor, judge, jurors/*
  skills/
    jje/             the orchestration loop + routing + verdict-contract pointer
    jje-contract/    the verdict JSON shape (preloaded into every juror)
    <lane>-review/   each juror's checklist + exact commands + blocking bar
  scripts/jje_state.py   deterministic counters, ledger, CI artifact, markers
  hooks/             jje-loop-guard.sh (budget/oscillation), jje-ci-gate.sh (commit gate)
  settings.json      hook wiring + deny rules
.jje/config.json     budget, presets, models, jurors
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and
[judge-jury-executioner.md](judge-jury-executioner.md) for the original spec.

## License

Apache-2.0. See [LICENSE](LICENSE).
