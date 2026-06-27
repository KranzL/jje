---
name: go-concurrency-review
description: The Go concurrency juror's checklist and exact commands — go test -race, go vet, staticcheck/golangci-lint, plus manual race/leak grep tells — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# go concurrency review
You review ONLY the Go concurrency surface: data races, goroutine/resource leaks, channel and mutex misuse, context cancellation and propagation. Stay in lane. Ignore style, security, and business logic.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem from lockfiles/config (go.mod, package.json, pyproject, Cargo.toml, dbt_project.yml, delta log, iceberg metadata). If there is no go.mod and no changed `.go` files, skip every check and emit ran[]=[] honestly.

## 2. Run the checks (gate each external tool on command -v)
For every external tool: `command -v <tool>` first; if absent, push to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags |
| --- | --- | --- |
| race detector (authoritative) | `go test -race ./...` | capture the `WARNING: DATA RACE` report verbatim |
| vet | `go vet ./...` | copylocks, loopclosure, lostcancel |
| staticcheck | `staticcheck ./...` | govet, contextcheck, noctx |
| golangci-lint | `golangci-lint run` | govet, contextcheck, noctx |

Manual grep tells (reasoning-led, cite file:line): `go func(` capturing a loop variable; writes to a shared map without a lock; a channel send/recv with no `select`/timeout; a context created without a matching `defer cancel()`; `sync.WaitGroup` Add/Done imbalance; goroutines with no exit path.

## 3. Blocking bar
Set blocking:true ONLY for: a real data race reported by `go test -race`; a goroutine/resource leak (a goroutine or context with no termination, a missing `defer cancel()`/`Close()`); or a deadlock-prone channel/mutex pattern. Cite the race report or the file:line. Everything else advisory; a finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-concurrency-juror.json, ran[]/skipped[] honest, id = gocc-<check>-<file>:<line>, nothing outside the JSON.
