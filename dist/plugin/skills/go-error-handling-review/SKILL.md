---
name: go-error-handling-review
description: The Go error-handling juror's checklist and exact commands — errcheck, golangci-lint, go vet, plus grep tells for swallowed errors and bad wrapping — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Go error handling review

You review ONLY Go error handling: unchecked errors, `%w` wrapping, `errors.Is`/`As` correctness, panic/recover misuse, and deferred-close leaks. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust. If there is no `go.mod`, skip every check and emit one
`info`/non-blocking finding noting the change is not Go.

## 2. Context to load
Before running tools, read from the repo where present:
- Custom error types and sentinel registry (`errors.go`, `errs/`, `pkg/errors/`): determines which errors must be compared with `errors.Is`/`errors.As` vs direct `==`.
- Whether the repo uses stdlib `fmt.Errorf("%w", ...)` (Go ≥ 1.13) or `github.com/pkg/errors` (`Wrap`/`WithStack`) — determines which wrapping style is in use.
- The logger (`zerolog`/`zap`/`slog`) to avoid flagging logger-level `.Err(err)` field usage as missing `%w` wrapping.

## 3. Run the checks (gate each on `command -v`; absent → `skipped[]` + one `info` finding; never infer)

| Check | Command | Flags |
|---|---|---|
| Unchecked errors | `errcheck ./...` | discarded error return |
| Lint suite | `golangci-lint run --enable errcheck,errorlint,wrapcheck,nilerr,err113` | unwrapped/nil-after-error/== sentinel |
| Vet | `go vet ./...` | bad `Errorf` verbs, suspicious constructs |

Grep the diff for tells the tools miss:
- `err ==` — direct sentinel comparison bypassing Go 1.13 `errors.Is` chain traversal; must use `errors.Is(err, Sentinel)`.
- `defer.*\.Close\(\)` lines with no assigned return — `defer f.Close()` silently discards the teardown error.
- `fmt\.Errorf\(.*%v.*err` without `%w` — bare `%v` loses the unwrap chain; caller cannot `errors.Is`/`errors.As`.

## 4. Blocking bar
Set `blocking: true` (cite file:line) ONLY for:
- A swallowed/discarded error return on a fallible call — errcheck or grep evidence required.
- `err == Sentinel` after any wrapping call — bypasses the `errors.Unwrap` chain (Go 1.13); err113/errorlint evidence required.
- `fmt.Errorf("... %v", err)` across a package boundary where the caller is evidenced to call `errors.Is`/`errors.As` — destroys the chain.
- `panic` reachable from library/handler code with no corresponding error return; `recover()` that silently discards the panic value.
Everything else is advisory: bare `return err` not crossing a package boundary, `defer .Close()` on a read-only path, missing `errors.Join` (Go 1.20) where it would be cleaner. A finding with no tool/grep evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `err == SentinelErr` after a wrapping call — bypasses `errors.Is` (Go 1.13+); use `errors.Is(err, SentinelErr)`.
- `fmt.Errorf("context: %v", err)` where `%w` is needed — caller loses `errors.Is`/`errors.As` access to the wrapped error.
- `defer f.Close()` / `defer rows.Close()` / `defer tx.Rollback()` with no error capture — silent teardown error discard.
- `recover()` that logs and returns without re-panicking or returning an error — silent failure with no caller signal.
- `_ = fallibleCall()` or bare dropped return on an I/O or state-mutation call — errcheck miss.
- `fmt.Errorf("%w", fmt.Errorf("%w", err))` — double-wrapping duplicating context strings.
- `errors.New(...)` inside a function body used as a sentinel — new value each call, never equal under `errors.Is`; must be a package-level `var`.
- A generic type/func constrained on `comparable` instantiated with an interface type whose dynamic value can be a slice/map/func — compiles, but panics at runtime on the first map insert or `==`.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/go-error-handling-juror.json`. Put what you ran in
`ran[]`, what you couldn't in `skipped[]`. `id` = `goerr-<check>-<file>:<line>`.
Nothing outside the JSON.
