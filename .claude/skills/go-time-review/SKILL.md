---
name: go-time-review
description: The go-time juror's checklist for time.Time equality operators, timezone-aware parsing, UTC storage discipline, clock-source testability, and calendar-vs-duration arithmetic.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# go time review
You review ONLY the Go `time` package contract: `time.Time` equality operators, timezone-aware parsing, UTC storage discipline, `time.Now` clock-source testability, and calendar-vs-duration arithmetic. PRINCIPAL level. Stay in lane: general Go correctness belongs to correctness-review; concurrency to go-concurrency-review; error handling to go-error-handling-review.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Filter CHANGED for `*.go`. Read changed Go files for `import "time"` and struct fields of type `time.Time` to establish all usage sites before running checks. If no Go files changed, emit empty findings.

## 2. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding)
- **Equality operators on time.Time**: grep `==` and `!=` across changed `.go` files; for each match read surrounding variable declarations to confirm `time.Time` typed operands. The `==` operator compares wall-clock, monotonic reading, AND Location pointer — two same-instant values compare unequal after a DB round-trip or `Round(0)`. Fix: `t.Equal(u)`.
- **Timezone-blind time.Parse**: grep `time\.Parse(` in changed files; inspect each layout string argument. Flag any layout with no UTC-offset marker (`Z07:00`, `-07:00`, `MST`, `Z`) on input documented or named as timezone-bearing — `time.Parse` silently assigns UTC, corrupting every non-UTC timestamp. Fix: `time.ParseInLocation` with an explicit `*time.Location`.
- **UTC storage discipline**: grep for DB or serialization write calls (`\.Exec(`, `\.Save(`, `\.Create(`, `json\.Marshal`, `proto\.Marshal`, `bson\.Marshal`) adjacent to `time.Time` values. Flag any `time.Time` written to a persistent store or wire format without an explicit `.UTC()` call — the server local zone is embedded, producing wrong ordering on retrieval in another region.
- **time.Now in domain/service functions**: grep `time\.Now()` in changed files; read the enclosing function name and receiver type. Flag any call not inside a dedicated clock provider, middleware, or test helper (not in `*_test.go`, not named `clock`/`now`/`tick`, not `main`). Fix: inject a `func() time.Time` parameter or a `Clock` interface.
- **Duration arithmetic for calendar intent**: grep `\.Add(` in changed files; read duration literals and surrounding comments. Flag any multiple of `24*time.Hour` or `30*24*time.Hour` where "next month", "next year", or "day boundary" is the stated intent — durations are fixed nanosecond counts that ignore DST transitions and variable month length. Fix: `time.Time.AddDate(years, months, days)`.
- **time.Local in production code**: grep `time\.Local` in changed non-test files. Flag explicit `time.Local` in struct initialization, `.In(time.Local)`, or `time.LoadLocation("Local")` calls in production packages — behavior depends on the host `TZ` env var, producing non-deterministic results across hosts. Prefer `time.UTC` or a named `*time.Location` loaded from config.
- **staticcheck SA1002**: if `command -v staticcheck`, run `staticcheck ./...` scoped to changed packages and surface any SA1002 (Invalid format in time.Parse) findings. Absent -> `skipped: ["staticcheck"]` + one info finding.

## 3. Blocking bar
Set `blocking: true` (cite file:line) ONLY for:
- A `time.Time ==` or `!=` comparison outside `reflect.DeepEqual` — silent logical inequality between same-instant values after any DB or network round-trip; data correctness defect.
- `time.Parse` with a timezone-blind layout on input documented or named as timezone-bearing — silently assigns UTC, corrupting every non-UTC timestamp stored or compared downstream.
- A `time.Time` written to a persistent store or wire format without `.UTC()` where the schema or downstream consumer is documented as UTC-only — produces wrong ordering and silent cross-region divergence.
Everything else is advisory: clock injectability; `time.Local` in production; duration-vs-calendar arithmetic; staticcheck SA1002 not meeting the above. A finding with no evidence is advisory by rule.

## 4. Anti-patterns to hunt
- `t1 == t2` or `t1 != t2` where both sides are `time.Time` — use `t1.Equal(t2)`.
- `time.Parse("2006-01-02 15:04:05", input)` — no zone in layout, timezone-bearing input silently coerced to UTC.
- `time.Parse("2006-01-02T15:04:05", input)` — missing `Z07:00` suffix; same silent-UTC defect.
- `db.Save(&record)` or `json.Marshal(record)` where `record.CreatedAt` is `time.Time` with no `.UTC()` immediately before.
- `time.Now()` inside a domain struct method or service function with no clock parameter on the signature.
- `event.Add(30 * 24 * time.Hour)` intended as "next month" — use `AddDate(0, 1, 0)`; `365 * 24 * time.Hour` intended as "next year" — use `AddDate(1, 0, 0)`.
- `.In(time.Local)` or `time.Local` in production struct initialization — host `TZ` dependency.

## 5. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to `iterations/iter-<n>/verdicts/go-time-juror.json`. `ran[]`/`skipped[]` honest. `id = gotime-<check>-<file>:<line>`. `check` field examples: `grep:time-equality`, `grep:timezone-parse`, `grep:utc-storage`, `grep:time-now-direct`, `grep:calendar-duration`, `grep:time-local`, `staticcheck:SA1002`. Nothing outside the JSON.
