---
type: eval-gauntlet
tags: [eval, e2e]
---
# End-to-end gauntlet — route validation

Real `/jje` runs on a private test repo, proving every route works cohesively
(the audit's "the loop has never looped" gap). Generic — no project specifics.
Companion to the engineered [[scorecard|fixture eval]].

| Route / scenario | Status | Notes |
|---|---|---|
| ACCEPT + **user-forced** REVISE (first real run) | **PASS** | full loop → PR; surfaced 4 prompt papercuts (all fixed) |
| **ESCALATE via contradiction** (#5) | **PASS** | Judge detected the contradiction **proactively at iter-1** (the smart path, not the oscillation/budget backstop); `record-contradiction` + ledger + clean exit; the conventions overlay reached each juror per-lane |
| **jury-forced** REVISE → ACCEPT (#3) | TODO | the loop converging on its own (vs the user-forced REVISE above) |
| ESCALATE via budget (#4) | TODO | |
| REPLAN (#6) | TODO | hardest to force with an LLM Executor |
| terraform scanner-required (#8) | TODO | tests the tool-backing fix (`tf-unverifiable`) |
| coverage-blind negative test (#12) | TODO | should wrongly ACCEPT a breaking change seated under `quick` |
| large multi-file PR, full panel (#11) | TODO | convergence vs thrash; false alarms reaching the Judge |

## Proven so far
- **The loop LOOPS end-to-end** — the audit's #1 gap, closed.
- **Interactivity** brokering (Planner/Executor/Judge return questions → orchestrator asks via AskUserQuestion → answers fed back) works across runs.
- **Conventions overlay** reaches jurors per-lane.
- **ESCALATE** exit + **contradiction detection** + ledger all work (smart path).
- CI-artifact gate, PR delivery, marker lifecycle, worktree GC, run lock — all clean.

## Still unproven
A **jury-forced REVISE→ACCEPT** (the core loop converging autonomously) and the
**large-PR stress** (full panel on a real diff). See [[hot|active threads]].
