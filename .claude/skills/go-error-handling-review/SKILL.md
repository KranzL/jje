---
name: go-error-handling-review
description: The Go error-handling juror's checklist and exact commands — errcheck, golangci-lint, go vet, plus grep tells for swallowed errors and bad wrapping — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Go error handling review

You review ONLY Go error handling: swallowed errors, error wrapping with `%w`,
sentinel/typed errors, panic/recover misuse. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust. If there is no `go.mod`, skip every check and emit one
`info`/non-blocking finding noting the change is not Go.

## 2. Run the checks (gate each on the tool being installed)
For every tool: `command -v <tool>` first. If absent, add it to `skipped[]` and
emit one `info`/non-blocking finding "`check skipped: <tool> not installed`".
Never infer what an un-run check would have found.

| Check | Command | Flags a |
|---|---|---|
| Unchecked errors | `errcheck ./...` | a returned error discarded |
| Lint suite | `golangci-lint run` (errcheck, errorlint, wrapcheck, nilerr) | unwrapped/lost/nil-after-error |
| Vet | `go vet ./...` | bad `Errorf` verbs, suspicious constructs |

Also grep the diff for the tells the tools miss: `_ = someCall()` or a bare
`someCall()` that returns an error and discards it; `fmt.Errorf("... %v", err)`
where `%w` is needed so the caller can `errors.Is`/`As`; `panic(` in a
non-`main` library/handler package; a `recover()` that swallows silently;
returning `nil` from inside or after an error branch.

## 3. Blocking bar
Set `blocking: true` ONLY for: a swallowed error on a fallible call; a `panic`
reachable from library/handler code that should return an error instead; or
error wrapping that loses the original the caller must inspect (breaks
`errors.Is`/`errors.As`). Cite the tool diagnostic or `file:line`. Everything
else is advisory (`warn`/`info`, `blocking: false`). A finding with no
tool/grep evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/go-error-handling-juror.json`. Put what you ran in
`ran[]`, what you couldn't in `skipped[]`. `id` = `goerr-<check>-<file>:<line>`.
Nothing outside the JSON.
