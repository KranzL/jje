---
name: go-db-sql-review
description: The go-db-sql juror's checklist for database/sql Rows/Stmt lifecycle, rows.Err discipline, transaction rollback discipline, context propagation, and connection pool ceiling in Go.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# go-db-sql review
You review ONLY the database/sql contract surface in Go: Rows/Stmt lifecycle, rows.Err() discipline after iteration, transaction rollback discipline, context propagation to query calls, and connection pool ceiling configuration. PRINCIPAL level. Stay in lane: generic error handling belongs to go-error-handling; SQL injection to security; query performance to query-performance-sql.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Filter to changed `.go` files that import `database/sql` or a wrapper: `grep -l 'database/sql\|jmoiron/sqlx\|jackc/pgx' $CHANGED 2>/dev/null`. Review only those.

## 2. Run the checks
Gate every external tool on `command -v`; absent → skipped[] + one info finding.

**rows.Close** — grep `\.Query\b\|\.QueryContext\b` in changed files; for each call site confirm `defer.*\.Close()` exists in the same function. If `golangci-lint` present: `golangci-lint run --enable sqlclosecheck --no-config ./...` on changed packages.

**rows.Err** — grep `rows\.Next()` in changed files; confirm `rows.Err()` is checked after every loop exits. If `golangci-lint` present: `golangci-lint run --enable rowserrcheck --no-config ./...`.

**Transaction rollback discipline** — grep `\.Begin\b\|\.BeginTx\b` in changed files; for each, confirm `defer.*Rollback()` appears before any `\.Commit()` call. Flag any `tx.Rollback()` call where the return error is not assigned: `grep -n 'tx\.Rollback()' $CHANGED | grep -Ev '(defer\s+tx\.Rollback|=\s*tx\.Rollback)'`.

**ErrNoRows handling** — grep `\.QueryRow\b` in changed files; confirm the Scan error path calls `errors.Is(err, sql.ErrNoRows)` to distinguish not-found from a query error.

**Non-context query variants** — `grep -n 'db\.Query[^C]\|db\.Exec[^C]\|db\.QueryRow[^C]' $CHANGED`; flag any match inside a function whose signature includes `context.Context`.

**Pool ceiling** — `git grep -n 'SetMaxOpenConns'`; flag if `sql.Open` is called with no `SetMaxOpenConns` call anywhere in the repository.

## 3. Blocking bar
Set `blocking: true` (cite file:line and tool output or grep match) ONLY for:
- `sql.Rows` from Query/QueryContext with no `defer rows.Close()` in the same function — live connection held until GC, pool starvation under burst load.
- `for rows.Next()` loop with no `rows.Err()` check after the loop — a network error mid-scan is silently treated as a complete result set.
- `db.Begin`/`db.BeginTx` with `tx.Commit()` but no `defer tx.Rollback()` — early return or panic between Begin and Commit leaves the transaction open and holds DB locks.
- Non-context `db.Query`/`db.Exec`/`db.QueryRow` called inside a function that receives `context.Context` — request cancellation does not propagate to the database.
Everything else is advisory: ErrNoRows not distinguished where all errors collapse to one path; missing SetMaxOpenConns in a CLI or test binary; non-context variants in init or test-only code. A finding with no evidence is advisory by rule.

## 4. Anti-patterns to hunt
- `rows, err := db.Query(...)` with no `defer rows.Close()` in the function body.
- `for rows.Next() { ... }` with no `if err := rows.Err(); err != nil` block after the loop.
- `tx, err := db.Begin(...)` with `tx.Commit()` but no `defer tx.Rollback()`.
- `row.Scan(...)` error path that does not call `errors.Is(err, sql.ErrNoRows)` when not-found is a distinct outcome.
- `db.Query(` / `db.Exec(` / `db.QueryRow(` (bare, no Context suffix) inside a handler or service method whose signature includes `ctx context.Context`.
- `sql.Open(...)` with no `db.SetMaxOpenConns(n)` visible anywhere in the repository — unlimited connections saturate the database server under burst traffic.

## 5. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-db-sql-juror.json, ran[]/skipped[] honest, id = gosql-<check>-<file>:<line>, nothing outside the JSON.
