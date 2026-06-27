---
name: go-performance-review
description: The Go performance juror's checklist and exact commands — benchmarks with -benchmem, escape analysis via -gcflags=-m, and hot-path allocation greps — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Go performance review

You review ONLY Go performance: heap allocations on hot paths, escape-analysis
regressions, unnecessary large-value copies, benchmark regressions. Four steps.
Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust. If there is no `go.mod`, this lane is not applicable — skip.

## 2. Run the checks (gate each on the tool being installed)
For every tool: `command -v <tool>` first. If absent, add it to `skipped[]` and
emit one `info`/non-blocking finding "`check skipped: <tool> not installed`".
Never infer what an un-run check would have found.

| Check | Command | Flags a |
|---|---|---|
| Benchmarks | `go test -bench . -benchmem ./...` | capture `ns/op` and `allocs/op`; compare to a baseline if benchmarks exist |
| Escape analysis | `go build -gcflags="-m" ./...` | `escapes to heap` on a hot path |

Also grep the diff for the allocation tells the tools confirm but don't surface:
`append` inside a loop with no `make([]T, 0, n)` prealloc; string concatenation
with `+` in a loop (use `strings.Builder`); `defer` inside a tight loop;
passing large structs by value; `regexp.Compile` inside a request path;
allocation in a per-element loop.

## 3. Blocking bar
Set `blocking: true` ONLY for: a new allocation hotspot or escape on a clearly
hot path; a measured benchmark regression; or unbounded buffer growth. Cite the
benchmark delta, the escape diagnostic, or `file:line`. Micro-optimizations with
no measured impact are advisory (`warn`/`info`, `blocking: false`). A finding
with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/go-performance-juror.json`. Put what you ran in
`ran[]`, what you couldn't in `skipped[]`. `id` = `goperf-<check>-<file>:<line>`.
Nothing outside the JSON.
