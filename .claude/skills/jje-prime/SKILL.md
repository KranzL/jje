---
name: jje-prime
description: Prime JJE for a repository — read its code, docs, and conventions, then seed the vault (Hot Cache + architecture map), draft PROPOSED project conventions for the jurors, and recommend a seating tier + ci_command. Read-only; it proposes, never gates.
argument-hint: <optional focus area or path>
allowed-tools: Agent, Task, Bash, Read, Write, Glob, Grep
---

# JJE prime — onboard a repository

You read a repository (and its docs) ONCE and synthesize the context JJE needs to
review it well: a seeded vault, draft project conventions for the jurors, and a
stack/lane/CI brief. This is **read-only** and **proposes** — it edits no source, runs
no build, and never activates a gating convention without the user's review.

First ensure `CLAUDE_PROJECT_DIR` is exported (it is often unset in a plain shell):
`: "${CLAUDE_PROJECT_DIR:=$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"; export CLAUDE_PROJECT_DIR`

The optional focus is `$ARGUMENTS` (a path or area to weight; default = the whole repo).

## 1. Survey the repo (parallel readers)
Spawn parallel reader subagents in a SINGLE message (your `Explore` or
`general-purpose` subagent) so they run concurrently; for a small repo you may read
directly. Cover these four areas, each returning a tight structured summary that cites
file paths as evidence and flags what it could NOT determine:
- **Stack & structure** — languages/frameworks from lockfiles (`go.mod`,
  `package.json`, `pyproject.toml`, `Cargo.toml`, `pom.xml`, `dbt_project.yml`, `*.tf`,
  Iceberg/Delta metadata), the directory map, entry points, and the build/test command
  (Makefile, CI YAML, package scripts → the `ci_command`).
- **Docs & architecture** — README, CONTRIBUTING, `docs/`, ADRs/RFCs, design docs,
  CHANGELOG: what the system does, its main components, and their boundaries.
- **Conventions-in-practice** — sample real source + config to infer the house rules:
  test framework/style, error-handling idiom, naming, module layout, logging, lint
  config (ruff/eslint/golangci-lint), formatting, type discipline, and any explicit
  rules stated in CONTRIBUTING/docs.
- **Risk & criticality** — where the gnarly/critical/security-sensitive code lives
  (auth, money, migrations, concurrency, data writes) and the lanes it implicates.

## 2. Write the seeded vault (real context, not skeleton)
Create `$CLAUDE_PROJECT_DIR/vault/` if absent, then write:
- `vault/hot.md` — the Hot Cache: a ~400-word "what this repo is, how it's built, where
  the risk lives, how to run its tests, and where JJE should be careful." Specific and
  evidence-grounded. Keep the `type: hot-cache` frontmatter; the SessionStart hook
  injects it into every future session.
- `vault/concepts/architecture.md` — the component/boundary map with file-path anchors.
- `vault/MOC.md` — the catalog linking the above.
Cite paths; never invent a component you did not see.

## 3. Draft PROPOSED conventions (review-gated — never auto-active)
Infer project-specific review rules from §1 and write them ONLY to
`$CLAUDE_PROJECT_DIR/.jje/conventions/PROPOSED.md` — NOT to an active
`.jje/conventions/*.md` file (those gate every run). Organize by `### <lane>` header
(lane names = juror domains, e.g. `correctness`, `security`, `structure`,
`go-error-handling`, `table-format`, `merge-upsert`, …). Mark each rule `(blocking)`
or `(advisory)`, and cite the file/pattern it was inferred from so the user can verify.
Propose ONLY a rule you saw real evidence for — an inferred-wrong `(blocking)` rule
causes false blocks. Open the file with:
`# PROPOSED conventions — review each rule, then move the ones you trust into a`
`# .jje/conventions/<lane>.md file to activate. Nothing here gates a run until you do.`

## 4. Brief the user (suggest, don't apply)
Print a short brief: detected stack → the recommended seating tier and the lanes/jurors
that apply; the detected `ci_command` (to paste into `.jje/config.json`); and a pointer
to the seeded vault + the PROPOSED conventions to review. Do NOT edit `config.json`
yourself — show the suggested values.

## Safety
Read-only by contract: no source edits, no build/CI execution, no activated convention.
Everything that could gate a future run (conventions, `ci_command`) is PROPOSED for the
user to apply. If unsure whether a rule or component is real, omit it.
