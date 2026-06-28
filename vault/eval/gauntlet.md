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
| overlay reaches juror + **no false-positive** (#10a) | **PASS** | convention was live, `structure-juror` ran with it, ACCEPT iter-1 — the juror correctly did NOT block a docstring that genuinely met the bar (Executor wrote `"""minutes per week; returns 'low','medium','high'"""`) |
| **jury-forced** REVISE → ACCEPT (#3/#10b) | TODO | **Finding:** two organic attempts (security #2, docstring-convention #10a) both ACCEPTed iter-1 because the **Sonnet Executor is too good** — it self-heals every tool-detectable defect *before commit* (runs the suite itself), so only defects that no tool catches AND that it wouldn't do by default survive to a juror. A "write a good docstring" rule fails that test (good docstrings are the default). Retry = scenario **10b**: an `__all__`-surface convention orthogonal to default practice (`scoring.py` has no `__all__`) — near-guaranteed block → REVISE → add to `__all__` → ACCEPT. |
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
