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
| **jury-forced** REVISE → ACCEPT (#10b) | **PASS** | The core loop converging **autonomously** (route was the Judge's, not a user override). iter-1 `structure-juror` blocked (`activity_tier` absent from `__all__`, the project convention) → Judge **REVISE** → iter-2 Executor added a full `__all__` → both jurors clean → **ACCEPT** → CI green → PR #3. Ledger: finding in `iterations:[1]` only, `recurring:0` → **resolved** (mirror of #5's recur→escalate). Took 3 tries to design: security #2 and docstring #10a both ACCEPTed iter-1 because the **Sonnet Executor is too good** — it self-heals every tool-detectable defect *before commit*, and writing a good docstring is its default. **Methodology lesson:** to force a jury-forced REVISE you need a convention *orthogonal to default good practice* (here: `__all__` membership, which `scoring.py` lacked) — not something a competent generator does anyway. |
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
The **large-PR stress** (full panel on a real multi-file diff — convergence vs
thrash, false alarms reaching the Judge) is the last headline route. The lower-value
backstops (budget-ESCALATE, REPLAN, terraform-scanner-required, coverage-blind) remain
optional. See [[hot|active threads]].

The **core loop is now fully proven**: ACCEPT, user-forced REVISE, **autonomous
jury-forced REVISE→ACCEPT** (#10b), and ESCALATE-via-contradiction (#5) have all run
clean end-to-end on a real repo.
