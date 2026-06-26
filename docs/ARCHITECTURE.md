# JJE architecture

JJE is four roles, one loop, one invariant, built on portable Claude Code
primitives. This document explains the moving parts and the decisions behind
them. The original design spec is [judge-jury-executioner.md](../judge-jury-executioner.md).

## The invariant

The loop operates on a **candidate**, never on the mainline. The Executor writes
to a scratch branch inside an isolated git worktree. Nothing reaches a protected
branch until the Judge returns ACCEPT and CI passes. A bad iteration costs a
re-run, not a revert — which is what makes the loop safe to run with light
supervision.

## Why the main agent orchestrates (and not nested subagents)

The load-bearing decision. A subagent cannot reliably spawn its own subagents
(Claude Code versions disagree on whether nesting works and how deep), so JJE
**never depends on nesting**. The main agent — driven by the `jje` skill — is the
only thing that spawns anything. Planner, Executor, every Juror, and the Judge
are all spawned at depth 1. This is the idiomatic Claude Code pattern and it
sidesteps the version-dependent nesting behavior entirely.

The consequence: orchestration logic lives in a **skill** (prose the main agent
follows), trustworthy state lives in a **CLI** (`jje_state.py`), and the hard
guarantees live in **hooks**. Each layer does what it is good at.

## The four layers

### 1. Orchestration — `skills/jje/SKILL.md`

A state machine the main agent follows: seed run → plan → seat jury → start
iteration → execute → jury (parallel) → guards → judge → route. The skill is the
only place the loop's control flow is written down. `routing.md` holds the
Judge's decision rules; `jje-contract` (a separate preloaded skill) holds the
verdict shape.

### 2. Roles — `agents/*.md`

Thin subagents (~5 lines each). The pattern is **thin agents, fat skills**: a
juror's system prompt says "review for X only, run the checks in
`skills/X-review`, emit one verdict"; the skill holds the actual commands and the
blocking bar. A reviewer's logic is then editable in one file while the agent
definition stays stable. Jurors preload `jje-contract` + their review skill via
the `skills:` frontmatter field so the contract and checklist are in context at
startup.

Model assignments follow cost: tool-backed jurors run on Haiku (mostly
formatting tool output into a verdict), high-judgment jurors (contract,
interface, idempotency, governance, correctness) on Sonnet, the Judge on Opus
(a wrong route is the most expensive mistake the loop can make).

### 3. Juror skills — `skills/<lane>-review/SKILL.md`

Each is self-contained and stack-agnostic: detect the ecosystem from lockfiles,
gate every external tool on `command -v`, push missing tools to `skipped[]` with
an advisory finding (never guess what an un-run check would have found), apply
the lane's blocking bar, emit one verdict. A lane that doesn't apply to the repo
(the dbt jurors on a pure-Go repo) no-ops with empty findings.

### 4. Safety — `scripts/jje_state.py` + two hooks + deny rules

- `jje_state.py` is the deterministic core: the authoritative iteration counter,
  the oscillation ledger (with a line-tolerant finding fingerprint), the CI
  result artifact, and the COMMIT_APPROVED marker. The model calls it; it never
  hand-edits the JSON.
- `jje-loop-guard.sh` (PreToolUse, matcher `Agent|Task`) fires on every Executor
  spawn and keeps its **own** counter, so termination is capped independently of
  whether the orchestrator remembered to advance the state CLI. It also blocks on
  a tripped oscillation guard.
- `jje-ci-gate.sh` (PreToolUse, matcher `Bash`) blocks every commit/merge/push
  while a run is active unless the marker exists, and blocks pushes to protected
  branches outright. The marker is single-use (consumed on a successful commit).
- `settings.json` deny rules are the unbypassable backstop for pushes to `main`.

## State model

One run directory per run: `.jje/runs/<run-id>/`.

| File | Writer | Purpose |
|---|---|---|
| `run.json` | `jje_state.py` only | counter, budget, status, branch, ci_command |
| `.jje/ACTIVE` | init / escalate / close | run lock; serializes runs and arms the commit gate |
| `plan.json` / `plan-v<n>.json` | Planner | the plan; replan keeps prior versions |
| `seating.json` | orchestrator | jurors seated this cycle |
| `iterations/iter-<n>/self-report.json`, `candidate.diff` | Executor | what changed |
| `iterations/iter-<n>/verdicts/<juror>.json` | each juror | one verdict each |
| `iterations/iter-<n>/decision.json` | `record-decision` | the Judge's route |
| `iterations/iter-<n>/ci-result.json` | `ci` | command, exit code, sha — the CI gate's evidence |
| `iterations/iter-<n>/executor-spawns` | loop-guard hook | model-independent spawn cap |
| `ledger.json` | `jje_state.py` only | finding fingerprints across iterations |
| `ESCALATION.md` | `escalate` | the human handoff |
| `.jje/COMMIT_APPROVED` | `accept` (consumed by hook) | the single-use commit token |

Each subagent writes its own output files and returns only a short pointer. This
keeps the main agent's context lean and leaves a full audit trail on disk.

## Termination

Two guards, both enforced deterministically:

- **Iteration budget** — `start-iteration` refuses past the cap; CI-failure
  bounces count against it; the loop-guard hook's independent counter is the hard
  backstop.
- **Oscillation guard** — `check-guards` fingerprints each blocking finding
  (`category + check + file + normalized issue`, line-tolerant) and flags any
  seen in ≥2 iterations as recurring → ESCALATE. The Judge names contradictory
  pairs (A demands X, fixing X trips B); `record-contradiction` forces escalate.

Escalation is a real exit: the loop stops and hands you the candidate branch plus
the open findings. Default policy is `stop`; `ship-with-caveats` is configurable
but still leaves the merge decision to you.

## CI is the gate, not a juror

The jury reviews; CI enforces. ACCEPT promotes the candidate into `jje_state.py
ci`, which runs the real CI command and records the exit code. `accept` mints the
commit marker only if that artifact says exit 0. The model reporting "CI passed"
is not sufficient — the artifact is.
