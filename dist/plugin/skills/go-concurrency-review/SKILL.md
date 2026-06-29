---
name: go-concurrency-review
description: The Go concurrency juror's checklist and exact commands — go test -race, go vet, staticcheck/golangci-lint, plus manual race/leak grep tells — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# go concurrency review
You review ONLY the Go concurrency surface: data races, goroutine and resource leaks, channel and mutex misuse, context cancellation and propagation. Stay in lane. Ignore style, security, and business logic.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem from lockfiles/config (go.mod, package.json, pyproject, Cargo.toml, dbt_project.yml, delta log, iceberg metadata). If there is no go.mod and no changed `.go` files, skip every check and emit ran[]=[] honestly.

## 2. Context to load
Read from the repo where present: `.jje/conventions` concurrency rules; the goroutine-lifecycle contract (how shutdown is signalled — context, channel, WaitGroup/errgroup); whether `golang.org/x/sync/errgroup` is the team standard for fan-out. Then anchor every finding to:
- **Go Memory Model** (go.dev/ref/mem) — the happens-before spec; every DATA RACE finding must name the guarantee violated.
- **sync/atomic** package contract — all accesses to a value must be atomic if any one access is; mixing `atomic.Store`/`atomic.Add` writes with plain reads is a data race.
- **golang.org/x/sync/errgroup** — idiomatic goroutine lifecycle + error propagation; flag raw `sync.WaitGroup` fan-out that cannot cancel on error.
- **uber-go/goleak** — de facto test-time goroutine leak detector; check whether `goleak.VerifyTestMain(m)` is wired into TestMain.

## 3. Run the checks (gate each external tool on `command -v`)
If absent, push to skipped[] and emit one info/non-blocking finding. Never infer what an un-run check would have found.

| Check | Command | Notes |
| --- | --- | --- |
| race detector (authoritative) | `go test -race ./...` | capture `WARNING: DATA RACE` verbatim |
| vet | `go vet ./...` | copylocks, loopclosure, lostcancel |
| golangci-lint | `golangci-lint run --enable=govet,contextcheck,noctx,bodyclose` | bodyclose catches resp.Body leaks |
| goleak | `go test -count=1 ./...` with `goleak.VerifyTestMain(m)` in TestMain | goroutine leak at test teardown |

Manual grep tells (cite file:line):
- `go func(` closing over loop variable without parameter pass — loop-variable race (go < 1.22 only; check go.mod before firing)
- map write inside a goroutine without `sync.Mutex`/`sync.RWMutex` — concurrent map write
- `sync\.Mutex` or `sync\.WaitGroup` in non-pointer function parameter or struct copy — copylocks
- `resp\.Body` without `defer.*\.Body\.Close(` in same function — transport goroutine leak
- `atomic\.Store\|atomic\.Add` write to a variable read elsewhere without `atomic\.Load` — happens-before violation
- `close(ch` followed by send on `ch` with no proven ordering guard — send-on-closed panic
- channel var initialized to `nil` with unconditional `<-` outside `select` — blocks forever

## 4. Blocking bar
Set blocking:true (cite race report or file:line with evidence) ONLY for:
1. Confirmed `WARNING: DATA RACE` from `go test -race` — quote the report verbatim; name the Go Memory Model guarantee violated.
2. `sync.Mutex` or `sync.WaitGroup` copied by value — behavior is undefined per the sync package docs; flagged by go vet copylocks.
3. Goroutine with no proven exit path — no context cancellation, channel close, or WaitGroup/errgroup Done reachable on every code path.
4. Send on a provably closed channel — runtime panic; cite both the `close` site and the send site.
5. `context.WithCancel`/`WithTimeout`/`WithDeadline` with no `defer cancel()` on a reachable non-error code path — context goroutine leak.
6. Non-atomic read of a variable written via `atomic.Store`/`atomic.Add` — data race per the sync/atomic package contract.

Everything else is advisory: potential leak not confirmed by race detector or goleak; missing errgroup where WaitGroup is technically correct; unbuffered channel with no proven deadlock path; `time.After` in a loop (timer leak, not an orphaned goroutine; go < 1.23 only — 1.23+ makes the timer GC-eligible once the channel is unreferenced; check go.mod before flagging); missing `goleak.VerifyTestMain` in TestMain. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `sync.Mutex` or `sync.WaitGroup` passed by value or copied into a struct — silently breaks the lock; copylocks violation.
- `resp.Body` not drained and closed — `net/http` transport goroutines block until Body is fully read and closed; require `defer resp.Body.Close()`.
- Send on a closed channel — runtime panic; flag `close(ch)` where a concurrent `ch <-` has no select guard or proven ordering.
- Receive on nil channel outside `select` — blocks the goroutine forever.
- `atomic.Store`/`atomic.Add` write with a plain (non-`atomic.Load`) read of the same variable — data race not surfaced by grep without tracing the write path.
- `go func(` closing over loop variable `i` or `v` by reference — require `v := v` shadow or explicit parameter pass (go < 1.22 only; go 1.22+ loop variables are per-iteration, skip if go.mod declares >= 1.22).
- `wg.Add(1)` called inside the goroutine body — races with `wg.Wait()`; Add must precede the `go` statement.
- `context.WithCancel` cancel called only on error branches — cancel goroutine leaks on the happy path.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-concurrency-juror.json, ran[]/skipped[] honest, id = gocc-<check>-<file>:<line>, nothing outside the JSON.
