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

Define the state helper as a shell **function** (a `S="…"` variable + `S init`
breaks in zsh — the default macOS shell — because zsh does not word-split
unquoted parameter expansions, so the very first command fails with exit 127):
`S(){ python3 "$CLAUDE_PROJECT_DIR/.claude/scripts/jje_state.py" "$@"; }`
Then call it as `S <subcommand> …` (no `$`), e.g. `S init --request "…"`.

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

## Interactivity (you broker every question to the user)
The Planner, Executor, and Judge are subagents — they CANNOT prompt the user.
You can. They return their open questions; **you ask the user with
AskUserQuestion and feed the answers back.** Read `interactivity.level` from
config (default `high`):
- `minimal` — never ask; run autonomously (CI/unattended). Skip all brokering.
- `normal` — ask only at genuine forks (a real ambiguity or an irreversible call).
- `high` (default) — ask at the start of every Plan, on every REVISE, and for any
  non-trivial Executor/Judge decision. Lean toward asking.
- `max` — ask aggressively, confirming even small calls; surface every returned
  question.

Brokering rule: whenever a role returns a `questions_for_user` /
`decisions_needed` / `clarifications` array, batch them (≤
`max_questions_per_turn`, default 4) into AskUserQuestion calls, then pass the
answers into the next spawn of that role. Make options concrete; put your
recommended option first. At `minimal`, pick sensible defaults and proceed.

## 0. Seed the run
1. `S init --request "$ARGUMENTS"` — capture `run_dir`, `scratch_branch`,
   `worktree`, `base_ref`, `budget`, `ci_command` from the JSON it prints. Use
   `RUN="<run_dir>"` below. If it errors that a run is already active, finish or
   `close` that run first (do not blindly `--force`).
2. Create the isolated candidate workspace:
   `git worktree add -b <scratch_branch> <worktree> <base_ref>`.
   Every Executor invocation operates ONLY in `<worktree>`.

## 1. Planner (callable; REPLAN returns here)
Spawn the `planner` subagent with the request and repo context. Instruct it to
write the plan to `$RUN/plan.json` (ordered steps, files in scope, risks,
explicit success criteria — these are what the jury checks against) and to return
a `questions_for_user` array (scope boundaries, approach choices, ambiguous
requirements, success criteria to confirm). It edits nothing.
**Broker `questions_for_user` per §Interactivity BEFORE you seat the jury** —
ask the user, then (if the answers change the plan) re-spawn the Planner with the
answers so the plan reflects them. On REPLAN, first `mv $RUN/plan.json
$RUN/plan-v<n>.json`, then re-spawn the Planner with the Judge's feedback (and
re-broker its new questions).

## 2. Seat the jury (user entry point; per cycle)
Read `presets` from `$CLAUDE_PROJECT_DIR/.jje/config.json` (fall back to
`config.example.json`). Use AskUserQuestion to present the roster (`quick`,
`code-full`, `pipeline`, `security-sweep`, `full`, `custom`). For `custom`, ask
a second multi-select over the 10 juror ids. Resolve the choice to a juror-id
list and write it to `$RUN/seating.json` as `{"seated": [...]}`.
Re-seat ONLY on REPLAN. On REVISE, reuse the existing `seating.json` unchanged.

## 3. Start an iteration (authoritative counter + budget)
Run `S start-iteration --run $RUN`.
- If it exits non-zero with `iteration_budget_exhausted`, go to ESCALATE (§8).
- Otherwise note the returned `iteration` number `<n>`.

## 4. Executor (build, or scoped revise)
Spawn the `executor` subagent, working dir = `<worktree>`. Pass `$RUN/plan.json`.
- First pass: build the candidate against the plan.
- On REVISE: pass the Judge's `feedback` (the specific blocking findings) and
  instruct it to fix ONLY those — no re-architecting.
Instruct it: when it hits a real fork (library/approach choice, an ambiguous
spec, an edge-case policy, a destructive or irreversible step), it must STOP and
return that fork in a `decisions_needed` array rather than guessing. **Broker
`decisions_needed` per §Interactivity, then re-spawn the Executor with the
answers** so it implements your choice. It commits on the scratch branch inside
the worktree, writes `$RUN/iterations/iter-<n>/self-report.json` (changed files,
plan steps covered, anything blocked, plus any `decisions_needed`), and snapshots
the diff to `$RUN/iterations/iter-<n>/candidate.diff`
(`git -C <worktree> diff <base_ref>`).

## 5. Jury (parallel, independent, scoped)
First, load any project conventions: if `$CLAUDE_PROJECT_DIR/.jje/conventions/`
holds `*.md` files, they carry project-specific review criteria under
`### <lane>` headers (see `.jje/conventions.example.md`). For each seated juror,
extract the section(s) whose lane matches the juror's domain (e.g.
`table-format-juror` → `### table-format`) and pass that text to the juror as
**PROJECT CONVENTIONS** — its `(blocking)` rules are additional blocking bars for
that lane. Pass only the matching section(s) to keep each juror's context lean.

Spawn ALL seated jurors in a SINGLE message as parallel spawns so they run
concurrently and never see each other's output. Give each: the worktree path,
the base ref (export `JJE_BASE=<base_ref>` so every juror diffs the same
baseline), `$RUN/plan.json`, its matching project conventions (if any), and the
iteration verdict dir. The Executor's self-report is **advisory context only** —
a juror must never set or clear `blocking` from what the Executor *claims*; only
its own checks and evidence decide.
Each juror writes exactly one verdict to
`$RUN/iterations/iter-<n>/verdicts/<juror>.json` matching
`skills/jje-contract/SKILL.md`. Do not let a juror comment outside its lane.

## 6. Guards, then Judge
1. `S check-guards --run $RUN`. This folds this iteration's blocking findings
   into the ledger and reports `recurring`, `contradictions`, `budget_remaining`,
   `recommend_escalate`.
2. Spawn the `judge` subagent (Read-only). Give it the verdict dir, the plan, the
   prior iterations' decisions, and the guard output. It reasons over verdicts
   (never re-reviews the candidate) and returns
   `{decision, rationale, feedback, unresolved, contradictions, clarifications}`
   per `skills/jje/routing.md`. The `clarifications` array holds genuinely
   judgment-dependent calls — a REVISE-vs-REPLAN boundary, whether a debatable
   advisory should gate, an ACCEPT with non-blocking caveats. **Broker
   `clarifications` per §Interactivity and let the user settle the call BEFORE you
   record the decision** (the user's answer can override the Judge's lean for
   anything except the hard `recommend_escalate` backstop). If the Judge names a
   contradictory pair, run `S record-contradiction --run $RUN --a <fpA> --b <fpB>
   --note "..."`.
3. Record it: `S record-decision --run $RUN --decision <D> --feedback "<...>"`.

If `recommend_escalate` is true, the decision MUST be ESCALATE regardless of the
Judge's lean or the user's answer (the guards are the hard backstop).

## 7. Route on the decision
- **ACCEPT** → §9 (CI gate).
- **REVISE** → keep the seated jury; return to §3 with the feedback for §4.
- **REPLAN** → return to §1 (new plan), then §2 (re-seat). Optionally reset the
  candidate: `git -C <worktree> reset --hard <base_ref>`.
- **ESCALATE** → §8.

## 8. Escalate (a real exit)
`S escalate --run $RUN --reason "<...>"`. Hand the user `$RUN/ESCALATION.md`,
the candidate branch, and the open findings. Then **run the §10 close-out** (Hot
Cache refresh/bootstrap) so the next session opens on the escalation, and stop.
(Default policy is `stop`. If config sets `escalation_policy: ship-with-caveats`,
the human still decides — JJE itself does not merge on escalate.)

## 9. CI = final gate
1. `S ci --run $RUN`. This runs `ci_command` inside `<worktree>` on the scratch
   branch and writes a verifiable `ci-result.json` (command, exit code, sha).
   Do NOT eyeball CI yourself — the artifact is what the gate trusts.
2. If it exits non-zero (CI FAILED): this counts against the budget — return to
   §3 and treat the failure as REVISE feedback for the Executor.
3. If CI is GREEN: `S accept --run $RUN`. This validates the CI artifact
   (exit 0, fresh, real sha) and only then writes `.jje/COMMIT_APPROVED`. Then
   land the candidate (ask the user — merge vs PR is outward-facing):
   - **Local merge to a protected branch:** the `jje-ci-gate` hook permits the
     single approved commit and **consumes** the marker.
   - **Open a PR** (`git push` the scratch branch + `gh pr create`): there is **no
     local protected-branch commit, so the marker is NOT consumed** by the push.
     That is fine — just do not leave it armed.
   Either way, finish with `S close --run $RUN`: it releases the run lock, GCs the
   worktree/branch, AND clears any unconsumed `.jje/COMMIT_APPROVED` so a stray
   future local commit can't be authorized by a leftover marker.

## 10. Close out — refresh the Hot Cache (auto-seeds on first run)
JJE keeps a small per-repo working memory at `$CLAUDE_PROJECT_DIR/vault/` so a
fresh session — and every future `/jje` run — starts with "where did we leave
off?" (the `jje-hot-cache` SessionStart hook injects `vault/hot.md`). It is local
working memory: **not** gitignored by default, so add `vault/` to `.gitignore` if
you don't want it committed.

This section runs on **both ACCEPT and ESCALATE** (escalations are exactly what the
next session needs to see first — §8 routes here before it stops). It is
**best-effort**: write only to **`$CLAUDE_PROJECT_DIR`** with absolute
`$CLAUDE_PROJECT_DIR/vault/...` paths (never the scratch worktree — `close` has
already GC'd it), and a write failure here must NOT unwind the accepted/merged
result or report the run as failed.

**Skip this whole section** (no bootstrap, no refresh) if config `hot_cache` is
`false`, OR if `interactivity.level` is `minimal` and `$CLAUDE_PROJECT_DIR/vault/`
does not already exist (unattended/CI must not *create* a vault — but it may refresh
one a user already keeps).

**Bootstrap:** if `$CLAUDE_PROJECT_DIR/vault/` does NOT exist, create it and seed
exactly three files, then tell the user one line: *"Seeded a local `vault/` for
cross-session memory — add it to `.gitignore` if you don't want it committed."*
Only create what is missing; never overwrite an existing file. Write the content
shown **between** the `~~~` fences below — the fences are display delimiters, NOT
file content; each file must begin with its `---` YAML frontmatter on line 1. Use
today's date for `<today>`.
- `$CLAUDE_PROJECT_DIR/vault/hot.md`:
  ~~~
  ---
  type: hot-cache
  updated: <today>
  tags: [meta, hot-cache]
  ---
  # Hot Cache — where did we leave off?

  > Read first. ~500-word cache of current state, overwritten each run.

  ## Last updated
  <today> — first JJE run on this repo.

  ## Key recent facts
  - (overwritten after each run)

  ## Active threads
  - (none yet)
  ~~~
- `$CLAUDE_PROJECT_DIR/vault/log.md`:
  ~~~
  ---
  type: log
  tags: [meta, log]
  ---
  # Run log (append-only)
  ~~~
- `$CLAUDE_PROJECT_DIR/vault/MOC.md`:
  ~~~
  ---
  type: moc
  tags: [meta, moc]
  ---
  # Map of Content
  JJE maintains `hot.md` (current state) and `log.md` (append-only) automatically.
  Add your own notes and link them here.
  ~~~

**Refresh** (the vault now exists, whether pre-existing or just bootstrapped):
1. **Overwrite** `$CLAUDE_PROJECT_DIR/vault/hot.md` with the new state — what this
   run changed, the key facts, and the open threads. It is a cache, not a journal:
   keep it under ~500 words, overwrite (do not append). Preserve the frontmatter and
   the `[[wikilink]]` style.
2. **Append** one dated line to `$CLAUDE_PROJECT_DIR/vault/log.md` summarizing the
   run (the log IS append-only).

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
