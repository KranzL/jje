---
type: concept
tags: [concept, seating, router, cost]
---
# Seating: tiers + an auto-router

How JJE decides **which jurors review a change**. Replaces the old hand-picked
lane-preset model (the user guessing `datalake` vs `go` vs `code-full`), which the
audit flagged as a human guess JJE should automate. Shipped d166b28.

## The model
- **Always-on core.** `correctness-juror` + `security-juror` are seated on every run,
  unconditionally.
- **Four tiers** (config `default_tier`, default `auto`):
  - `quick` — core only.
  - `auto` — core + the lanes the change **clearly** touches (router-chosen).
  - `full` — core + every lane it **plausibly** touches (thorough).
  - `custom` — start from the core, user adds the rest (router not run).
- **The [[router|router agent]]** (Haiku, Read-only) reads the finalized `plan.json`
  (`files_in_scope` + request + risks — there is **no diff yet**, seating precedes the
  build in [[jje-loop|§2]]) and maps scope → lanes by each juror's `lane` field, then
  returns `{seated, added, considered_but_skipped}` with a per-lane rationale.

## Why this shape
- **No human preset guess.** The router knows the lane→signal map (`*.tf`→terraform,
  `*.go`→Go jurors, a changed public signature→interface-compat, …) better than a user
  picking a bundle name.
- **Cost.** Seats only relevant lanes — a pure-Python change never spins up 33 no-op
  data/IaC jurors. (The audit's #1 cost lever.)
- **The user still owns it.** Two hard requirements (user feedback) the redesign had to
  meet, both now satisfied:
  1. seating is a GENUINE user multi-select — the router *pre-checks*, the user *edits*;
  2. no silent truncation behind AskUserQuestion's **4-option cap** — the core is
     non-removable (shrinks the choice set), the edit paginates across questions, and a
     free-text `add <id>`/`drop <id>` escape reaches the full roster.

## Gotchas the verification pass caught
- The router must emit **exact `-juror` ids** (abbreviated lane labels won't spawn).
- **Greenfield** not-yet-created files route by extension/path, not the
  "unreadable→code" fallback (that fallback is only for a missing/unparseable plan).
- `custom` + non-asking interactivity (`normal`/`minimal`) falls back to `auto` rather
  than silently seating core-only.
- A `presets` entry is **not** a lane (e.g. the `pipeline` preset omits
  `governance-juror`); presets are only `custom` shorthand, not what the router seats by.

## Status
Built + verified by adversarial review; **not yet exercised in a live `/jje` run** —
the next validation is a werkschau shakedown. See [[hot]].
