---
type: hot-cache
updated: 2026-06-28
tags: [meta, hot-cache]
---
# Hot Cache — where did we leave off?

> Read this first. ~500-word cache of current state, **overwritten each session**.
> Full map: [[MOC]].

## Last updated
**2026-06-28** — The [[jje-loop|loop ran end-to-end for real]] for the first time;
fixed the 4 papercuts it surfaced.

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
1. **Finish the gauntlet** ([[gauntlet]]): the **core loop is fully proven** —
   ACCEPT, user-forced REVISE, **autonomous jury-forced REVISE→ACCEPT** (#10b ✓,
   the `__all__`-convention orthogonal trick), ESCALATE/contradiction (#5 ✓). Last
   headline route = **large multi-file PR, full panel** (#11). Backstops
   (budget-ESCALATE, REPLAN, terraform-scanner, coverage-blind) optional.
   **Lesson (#10b):** forcing a jury-forced REVISE needs a convention *orthogonal to
   default good practice* — the Sonnet Executor self-heals anything tool-detectable
   before commit, so realistic single-fn defects ACCEPT on iter-1.
2. **[DECIDED — build after the gauntlet] Seating redesign.** Always-on **core**
   (correctness + security, seated on every run) + a **Haiku diff-router** that
   adds only the lane specialists the diff warrants. Retire the per-lane presets;
   keep tiers `quick` / `auto` (default) / `full` / `custom`. Replaces
   "which preset?" (a human guess JJE should automate) and slashes cost. This is
   the audit's #1 build, now with an agreed shape.
   **Hard requirements (user feedback, two parts):**
   (a) `custom`/`auto` seating must be a GENUINE user multi-select — the router
   pre-checks its recommendations but the USER edits; never pre-decide the set
   under a "custom" label.
   (b) The custom picker must surface the FULL relevant roster, not a single
   4-item page. Root cause: AskUserQuestion hard-caps at **4 options**, so a flat
   "see all 38 and pick" is impossible in one widget — it can only show the top-4,
   which silently hides relevant jurors on multi-lane changes (e.g. the large-PR
   #11). Fix paths: the **router auto-seats** relevant lanes (so the human rarely
   scrolls), plus a **hierarchical/paginated** manual picker (lane-group → jurors,
   or multi-step) for override. The redesign owns both.
3. **Prompt caching** the shared juror prefix — ~90% off the replicated input.
4. **Coverage check + Judge evidence spot-read** — ACCEPT = "no seated juror
   objected", not "correct". See [[jje-loop]].
5. Model right-sizing (31/38 on Sonnet vs the haiku default); skipped-core →
   escalate systemically; caveman ONLY on Judge/Planner/Executor prose.
