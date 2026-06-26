---
name: jje
description: Run the Judge-Jury-Executioner generator-critic loop. Drives Planner, Executor, a seated panel of parallel jurors, and the Judge over a candidate on a scratch branch, with an iteration budget, an oscillation guard, and CI as the final commit gate.
argument-hint: <request describing the change to make>
allowed-tools: Agent, Task, Bash, Read, Write, AskUserQuestion
---

# JJE orchestration loop

You are the orchestrator. You drive the loop on PORTABLE primitives only: you
spawn every subagent yourself (no nested spawning), you keep trustworthy state
by calling `jje_state.py` (never hand-edit the JSON), and you let the hooks
enforce the hard guarantees. Do the steps in order. Use absolute paths.
`S="python3 $CLAUDE_PROJECT_DIR/.claude/scripts/jje_state.py"`.

> **Spawn tool name:** this guide says "spawn the `<role>` subagent". Use your
> subagent-spawn tool — it is named `Agent` (older Claude Code calls it `Task`);
> both take a `subagent_type` parameter. The loop-guard hook matches either.

The request is `$ARGUMENTS`.

## Invariant (do not violate)
The loop operates on a CANDIDATE, never on mainline. The Executor edits only
inside an isolated worktree on a scratch branch. Nothing reaches a protected
branch until the Judge returns ACCEPT and CI is green. While a run is active the
`jje-ci-gate` hook blocks every commit/merge/push without the approval marker;
do not try to work around it.

## 0. Seed the run
1. `$S init --request "$ARGUMENTS"` — capture `run_dir`, `scratch_branch`,
   `worktree`, `base_ref`, `budget`, `ci_command` from the JSON it prints. Use
   `RUN="<run_dir>"` below. If it errors that a run is already active, finish or
   `close` that run first (do not blindly `--force`).
2. Create the isolated candidate workspace:
   `git worktree add -b <scratch_branch> <worktree> <base_ref>`.
   Every Executor invocation operates ONLY in `<worktree>`.

## 1. Planner (callable; REPLAN returns here)
Spawn the `planner` subagent with the request and repo context. Instruct it to
write the plan to `$RUN/plan.json` (ordered steps, files in scope, risks,
explicit success criteria — these are what the jury checks against). It edits
nothing. On REPLAN, first `mv $RUN/plan.json $RUN/plan-v<n>.json`, then re-spawn
the Planner with the Judge's feedback.

## 2. Seat the jury (user entry point; per cycle)
Read `presets` from `$CLAUDE_PROJECT_DIR/.jje/config.json` (fall back to
`config.example.json`). Use AskUserQuestion to present the roster (`quick`,
`code-full`, `pipeline`, `security-sweep`, `full`, `custom`). For `custom`, ask
a second multi-select over the 10 juror ids. Resolve the choice to a juror-id
list and write it to `$RUN/seating.json` as `{"seated": [...]}`.
Re-seat ONLY on REPLAN. On REVISE, reuse the existing `seating.json` unchanged.

## 3. Start an iteration (authoritative counter + budget)
Run `$S start-iteration --run $RUN`.
- If it exits non-zero with `iteration_budget_exhausted`, go to ESCALATE (§8).
- Otherwise note the returned `iteration` number `<n>`.

## 4. Executor (build, or scoped revise)
Spawn the `executor` subagent, working dir = `<worktree>`. Pass `$RUN/plan.json`.
- First pass: build the candidate against the plan.
- On REVISE: pass the Judge's `feedback` (the specific blocking findings) and
  instruct it to fix ONLY those — no re-architecting.
Instruct it to commit on the scratch branch inside the worktree, write
`$RUN/iterations/iter-<n>/self-report.json` (changed files, plan steps covered,
anything blocked), and snapshot the diff to
`$RUN/iterations/iter-<n>/candidate.diff` (`git -C <worktree> diff <base_ref>`).

## 5. Jury (parallel, independent, scoped)
Spawn ALL seated jurors in a SINGLE message as parallel spawns so they run
concurrently and never see each other's output. Give each: the worktree path,
the base ref (export `JJE_BASE=<base_ref>` so every juror diffs the same
baseline), `$RUN/plan.json`, the self-report, and the iteration verdict dir.
Each juror writes exactly one verdict to
`$RUN/iterations/iter-<n>/verdicts/<juror>.json` matching
`skills/jje-contract/SKILL.md`. Do not let a juror comment outside its lane.

## 6. Guards, then Judge
1. `$S check-guards --run $RUN`. This folds this iteration's blocking findings
   into the ledger and reports `recurring`, `contradictions`, `budget_remaining`,
   `recommend_escalate`.
2. Spawn the `judge` subagent (Read-only). Give it the verdict dir, the plan, the
   prior iterations' decisions, and the guard output. It reasons over verdicts
   (never re-reviews the candidate) and returns
   `{decision, rationale, feedback, unresolved, contradictions}` per
   `skills/jje/routing.md`. If the Judge names a contradictory pair, run
   `$S record-contradiction --run $RUN --a <fpA> --b <fpB> --note "..."`.
3. Record it: `$S record-decision --run $RUN --decision <D> --feedback "<...>"`.

If `recommend_escalate` is true, the decision MUST be ESCALATE regardless of the
Judge's lean (the guards are the hard backstop).

## 7. Route on the decision
- **ACCEPT** → §9 (CI gate).
- **REVISE** → keep the seated jury; return to §3 with the feedback for §4.
- **REPLAN** → return to §1 (new plan), then §2 (re-seat). Optionally reset the
  candidate: `git -C <worktree> reset --hard <base_ref>`.
- **ESCALATE** → §8.

## 8. Escalate (a real exit)
`$S escalate --run $RUN --reason "<...>"`. Hand the user `$RUN/ESCALATION.md`,
the candidate branch, and the open findings, then stop. (Default policy is
`stop`. If config sets `escalation_policy: ship-with-caveats`, the human still
decides — JJE itself does not merge on escalate.)

## 9. CI = final gate
1. `$S ci --run $RUN`. This runs `ci_command` inside `<worktree>` on the scratch
   branch and writes a verifiable `ci-result.json` (command, exit code, sha).
   Do NOT eyeball CI yourself — the artifact is what the gate trusts.
2. If it exits non-zero (CI FAILED): this counts against the budget — return to
   §3 and treat the failure as REVISE feedback for the Executor.
3. If CI is GREEN: `$S accept --run $RUN`. This validates the CI artifact
   (exit 0, fresh, real sha) and only then writes `.jje/COMMIT_APPROVED`. Open a
   PR / merge from the scratch branch; the `jje-ci-gate` hook permits the single
   approved commit and consumes the marker. Then `$S close --run $RUN` to release
   the run lock.

## State files (who writes what)
| File | Writer |
|---|---|
| `run.json` (counter, budget, status, branch) | `jje_state.py` only |
| `.jje/ACTIVE` (run lock, arms the gate) | `jje_state.py` init / cleared by escalate/close |
| `plan.json` / `plan-v<n>.json` | Planner |
| `seating.json` | orchestrator (you) |
| `iterations/iter-<n>/self-report.json`, `candidate.diff` | Executor |
| `iterations/iter-<n>/verdicts/<juror>.json` | each juror |
| `iterations/iter-<n>/decision.json` | `jje_state.py record-decision` (from Judge output) |
| `iterations/iter-<n>/ci-result.json` | `jje_state.py ci` |
| `iterations/iter-<n>/executor-spawns` | loop-guard hook (model-independent cap) |
| `ledger.json` (oscillation guard) | `jje_state.py` only |
| `ESCALATION.md` | `jje_state.py escalate` |
| `.jje/COMMIT_APPROVED` | `jje_state.py accept` (consumed by hook) |
