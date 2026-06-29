---
name: go-performance-review
description: The Go performance juror's checklist and exact commands — benchmarks with -benchmem and benchstat, escape analysis via -gcflags="-m -m", pprof, and hot-path allocation greps — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Go performance review

You review ONLY Go performance: heap allocations on hot paths, escape-analysis regressions, unnecessary large-value copies, and benchmark regressions. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust. If there is no `go.mod`, this lane is not applicable — skip.

## 2. Context to load
Read the repo for: existing `*_test.go` benchmark functions (baseline exists or not); which code paths are hot — HTTP handlers, iterators, per-element loops, functions visible in any committed pprof profiles; whether `GOGC`/`GOMEMLIMIT` (`runtime/debug.SetMemoryLimit`, Go 1.19+) are tuned in config/env; whether `sync.Pool` is already in use on known alloc-heavy paths. Without a baseline benchmark or escape-analysis output, a finding on a non-loop path is advisory by rule.

## 3. Run the checks (gate each tool on `command -v`; absent → `skipped[]` + one info finding; never infer)

| Check | Command |
|---|---|
| Benchmarks | `go test -bench . -benchmem -count=10 ./...` — annotate benchmarks with `testing.B.ReportAllocs()` and `testing.B.SetBytes(n)` to make allocs/op and B/s first-class output |
| Benchmark comparison | `benchstat old.txt new.txt` (golang.org/x/perf/cmd/benchstat) — blocking if the CI excludes zero AND delta ≥ 10% ns/op, or any allocs/op increase on a hot path |
| Escape analysis | `go build -gcflags="-m -m" ./...` — double `-m` surfaces second-level inlining failures and closure-capture reasons that single `-m` silently elides |
| CPU/heap profile | `go test -cpuprofile cpu.prof -memprofile mem.prof -bench . ./...` then `go tool pprof -top cpu.prof` — run only if profiles or a profiling harness exist in the repo |

Grep the diff for allocation tells the tools confirm but don't surface alone:
- `grep -n 'append(' <file>` — flag append inside a loop with no preceding `make([]T, 0, n)` cap hint
- `grep -n 'defer ' <file>` — flag defer inside a loop body (not open-coded by the compiler in loop context)
- `grep -n 'fmt\.Sprintf\|fmt\.Fprintf' <file>` — flag on any hot path (reflection + allocation each call)
- `grep -n 'regexp\.Compile\|regexp\.MustCompile' <file>` — flag inside a called function; must be a package-level var
- `grep -n 'interface{}\|\ any$\| any ' <file>` — flag in signatures of functions called inside loops (boxing forces heap escape)

## 4. Blocking bar
Set `blocking: true` (cite file:line and evidence) ONLY for:
1. Escape analysis (`-gcflags="-m -m"`) reports `escapes to heap` at a call site inside a loop, iterator method, or per-request HTTP handler — and the allocation is new or regressed in this diff.
2. benchstat CI excludes zero AND ≥ 10% ns/op regression on an existing benchmark, OR any increase in allocs/op on a path identified as inside a loop or per-request handler.
3. Unbounded slice or map growth: `append`/map literal inside a loop with no capacity hint and no proven upper bound — memory cliff under load.

Everything else is advisory: micro-optimizations with no measured impact; ns/op shifts below benchstat's significance threshold; missing `sync.Pool` where allocation is not on a measured hot path; `GOGC`/`GOMEMLIMIT` tuning suggestions; cache-line padding; large-struct-by-value on an unconfirmed cold path. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `interface{}` / `any` in signatures of functions called inside loops — boxing escapes to heap; grep `interface{}\|any` at call sites within loop bodies.
- `fmt.Sprintf`/`fmt.Fprintf` on a hot path — reflection + allocation per call; use `strings.Builder` + `strconv` or `fmt.Appendf` (Go 1.19+).
- `defer` inside a loop body — defers are not open-coded by the compiler when inside a loop; accumulates deferred frames until the enclosing function returns.
- String concatenation with `+` inside a loop — allocates a new string per iteration; use `strings.Builder`.
- `regexp.Compile`/`regexp.MustCompile` inside a called function rather than a package-level or `sync.Once`-initialized var — re-compiles on every call.
- `encoding/json` `Marshal`/`Unmarshal` in a tight loop or per-request handler without a pool or pre-allocated buffer — reflection-heavy; flag and require profile evidence before blocking.
- Hot struct missing `sync.Pool` when the same large allocation is made on every request and GC pressure is measured — absence of pooling IS the finding once the path is confirmed hot.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/go-performance-juror.json`. Put what you ran in
`ran[]`, what you couldn't in `skipped[]`. `id` = `goperf-<check>-<file>:<line>`.
Nothing outside the JSON.
