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
| large multi-file PR, full panel (#11) | **PASS** | 5-file +416/−36 gh_api cache feature, `code-full` panel (5 jurors), PR #4. **Converged in 3/6 iterations** (REVISE→REVISE→ACCEPT) with monotonically decreasing findings — no thrash, no oscillation. **1 blocking total** across 15 verdicts (observability: uncaught `OSError` on cache write — a real crash-on-long-extraction bug). **False-alarm rate ≈ 0**: 4 advisories total, ALL legitimate and actioned (perms `0o644`→`0o600/0o700`, auth-identity-in-key doc note, legacy-dir `chmod(0o700)`, a test-honesty note); `structure` + `interface-compat` stayed silent (no nitpicking). Security found the real hardening issues — the Executor preempted path-traversal by using SHA-256 keys, so security correctly focused on file perms. interface-compat correctly **cleared** the `gh_api` signature change (back-compat wrappers preserved). **Key finding: the audit's 17-false-alarm worry did NOT reproduce on a real change** — engineered fixtures with planted distractors trip jurors; a well-planned real diff from a competent Executor reviews precisely. |

## Proven so far
- **The loop LOOPS end-to-end** — the audit's #1 gap, closed.
- **Interactivity** brokering (Planner/Executor/Judge return questions → orchestrator asks via AskUserQuestion → answers fed back) works across runs.
- **Conventions overlay** reaches jurors per-lane.
- **ESCALATE** exit + **contradiction detection** + ledger all work (smart path).
- CI-artifact gate, PR delivery, marker lifecycle, worktree GC, run lock — all clean.

## Gauntlet complete — every headline route proven on a real repo
- **ACCEPT** (first real run) ✓
- **user-forced REVISE → ACCEPT** (calendar) ✓
- **autonomous jury-forced REVISE → ACCEPT** (#10b, the `__all__` orthogonal trick) ✓
- **ESCALATE via contradiction** (#5, Judge caught it proactively) ✓
- **large multi-file PR, full 5-juror panel** (#11, 3-iter convergence, ~0 false alarms) ✓

The biggest open audit worry — false-alarm spam from the panel — was **measured and
did not reproduce** on a real change (#11: 4 advisories, all legitimate). The cross-
juror-correlation and coverage-blind concerns remain theoretical here.

### Optional backstops (lower value, not yet exercised live)
budget-ESCALATE (#4 — partially shadowed by #11's budget headroom), REPLAN (#6 —
hardest to force with a capable Executor), terraform-scanner-required (#8 — would
test the `tf-unverifiable` tool-backing fix, needs a TF diff), coverage-blind (#12).
None are on the critical path. See [[hot|active threads]].
