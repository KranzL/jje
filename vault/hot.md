---
type: hot-cache
updated: 2026-06-28
tags: [meta, hot-cache]
---
# Hot Cache — where did we leave off?

> Read this first. ~500-word cache of current state, **overwritten each session**.
> Full map: [[MOC]].

## Last updated
**2026-06-28** — **The [[gauntlet]] is complete** (every headline route proven on
werkschau: ACCEPT, user-forced REVISE, autonomous jury-forced REVISE→ACCEPT,
ESCALATE-via-contradiction, large multi-file full-panel PR #11). Also: made the
[[hot|Hot Cache]] borrowable, AND **shipped the [[seating-router|seating redesign]]**
(tiers + Haiku router, d166b28). Both hardened via adversarial verify passes.

## Key recent facts
- **JJE** = a generator–critic review harness for Claude Code, public at
  `github.com/KranzL/jje`. Roster **38 jurors / 11 lanes / 14 presets**.
- **THE LOOP HAS NOW LOOPED.** A real `/jje` run on a private test repo went all
  the way to a shipped PR — Planner + brokered questions, jury, Judge **ACCEPT**,
  a **user REVISE-override** of the Judge, iter-2 ACCEPT, CI gate, PR delivery,
  clean close. This closes the audit's biggest gap (it had only ever run once,
  trivially).
- The run surfaced 4 papercuts, all in **prompts/skill, not the state machine**
  (the CLI core held up) — now fixed (commit e1b9a04): the zsh-breaking `S=` helper
  → a shell function; Planner/Executor `git check-ignore` scope files; the Judge no
  longer offers a phantom "fast follow-up" (ACCEPT is terminal); marker-on-PR-path
  documented.
- Biggest lever remains [[tool-backing]] (proven by [[scale-eval]]); the 3 scale
  missers are now tool-backed.
- Safety hooks are **conditional** (trusted + non-bypass) — see [[safety-model]].
- A private test repo is staged with the **fixed** harness + the full
  [[#Active threads|12-scenario gauntlet]] (`JJE-GAUNTLET.md`).

## Recent changes
- **Strengthened all 38 [[jurors]] to industry-standard depth** (c0bcc44): audited
  vs the `data-leakage` gold standard, then deepened each (named canon + real numbers
  + quantified checks + anti-pattern hunt + crisp blocking bar; uniform 47–74 lines).
  Hardened via **3 adversarial fact-check rounds** — the generators over-reached and
  invented plausible specifics; the checkers caught them (Avro compat direction, Kargo
  fields, IEEE-754 log(0), flag renames); converged with a correct-or-remove rule + 7
  manual fixes. **Lesson: LLM-authored dense domain facts have a high error rate —
  generate-then-fact-check (and bias to removal) is mandatory, not optional.**
- **Made the [[hot|Hot Cache]] actually borrowable** (it was inert for any user
  without a hand-built vault): §10 now **auto-seeds `vault/` on first run**, added a
  real `hot_cache` config off-switch (honored by the hook + §10), hardened via an
  adversarial verify pass (absolute paths, CI/`minimal` gating, escalate routes
  through §10, jq `//`-bug fixed). See README "Hot Cache". (94631c7)
- Fixed the 4 first-run papercuts; re-synced the test repo's harness with the fix.
- Wired the [[hot|Hot Cache]] into the loop (SessionStart hook + /jje close-out).
- Built the assumptions/token audit + the [[scale-eval|3-pass eval]].

## Active threads
Highest leverage first (audit-ranked):
1. **[DONE ✓] Gauntlet** ([[gauntlet]]) — every headline route proven on werkschau
   (ACCEPT, user/jury-forced REVISE, ESCALATE-via-contradiction, large-PR #11). The
   audit's #1 worry (panel false-alarm spam) did NOT reproduce on a real change.
   Optional backstops remain (budget-ESCALATE, REPLAN, terraform-scanner, coverage-blind).
   **Lessons:** (a) forcing a jury-forced REVISE needs a convention *orthogonal to
   default good practice*; (b) false-alarm spam is a *fixture* artifact, not real-diff.
2. **[DONE ✓] [[seating-router|Seating redesign]]** (d166b28) — tiers
   `quick`/`auto`(default)/`full`/`custom` + a Haiku `router` that seats the
   correctness+security core plus only the lanes the plan touches; the user always
   edits. Both custom-picker requirements met (genuine multi-select; no silent 4-cap
   truncation, via free-text add/drop). Verified via an adversarial pass (~12 fixes).
   **Live (werkschau 2026-06-28): tier question + genuine custom multi-select +
   core-non-removable all validated; the Hot Cache bootstrap also fired correctly
   (project-dir path, frontmatter line 1). PENDING: the `auto` router path itself —
   that run chose `custom` (skips the router); one `auto` run closes it.**
3. **Prompt caching** the shared juror prefix — ~90% off the replicated input.
4. **Coverage check + Judge evidence spot-read** — ACCEPT = "no seated juror
   objected", not "correct". See [[jje-loop]].
5. Model right-sizing (31/38 on Sonnet vs the haiku default); skipped-core →
   escalate systemically; caveman ONLY on Judge/Planner/Executor prose.
