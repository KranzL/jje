---
name: correctness-review
description: The correctness juror's checklist and exact commands — run the test suite by ecosystem, reason about edge cases and complexity — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Correctness review

You review ONLY logic, edge cases, and algorithmic complexity. Four steps.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem: `go.mod` → Go, `package.json` → JS/TS,
`pyproject.toml`/`requirements.txt` → Python, `Cargo.toml` → Rust.

## 2. Run the tests (gate each on the tool being installed)
`command -v <tool>` first; if absent, add to `skipped[]` and emit one
non-blocking `info` finding. Prefer running the tests that exercise the changed
code; fall back to the suite.

| Ecosystem | Command |
|---|---|
| Python | `pytest -q` (or `pytest <changed test paths> -q`) |
| Go | `go test ./...` |
| Rust | `cargo test` |
| JS/TS | `npm test --silent` / `pnpm test` / `yarn test` (whichever the repo uses) |

Capture failing test node ids verbatim — they are your evidence and must be
stable across iterations.

## 3. Reason where tools can't reach
The success_criteria in `plan.json` are the spec — check the candidate against
them. Beyond pass/fail, reason about: unhandled edge cases (empty/None, zero,
negative, boundary, unicode, overflow), off-by-one and wrong comparison, error
paths that swallow or mis-handle, concurrency/ordering assumptions, and
algorithmic complexity on hot paths (a new O(n^2)/unbounded loop over input).

## 4. Blocking bar
Set `blocking: true` for: a failing test caused by this change; wrong output
against a success criterion; a real unhandled edge case that produces incorrect
behavior; unbounded complexity on a hot path. A complexity worry with no concrete
triggering input is advisory. A finding with no evidence (test name / reproducing
input / line) is advisory.

## 5. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/correctness-juror.json`. `id` =
`corr-<check>-<file>:<line>` (use the test node id as `<check>` for test
failures). `ran[]`/`skipped[]` honest. Nothing outside the JSON.
