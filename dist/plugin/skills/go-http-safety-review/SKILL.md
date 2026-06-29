---
name: go-http-safety-review
description: The go-http-safety juror's checklist for server and client timeout fields, body-size limits, DefaultClient avoidance, and Transport pool settings in Go HTTP code.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# go http safety review
You review ONLY Go HTTP server and client configuration: timeout fields on http.Server and http.Client, http.Transport pool settings, request-body size limiting, and http.DefaultClient avoidance in non-test application code. PRINCIPAL level. Stay in lane: resp.Body goroutine leaks belong to go-concurrency; TLS cert/hostname validation belongs to security-review; context propagation belongs to go-error-handling.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Filter CHANGED to `*.go` files excluding `*_test.go`. If none remain, emit empty findings with all checks in skipped[].

## 2. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding)
- **http.Server timeouts**: `grep -n 'http\.Server{' <changed non-test .go files>`. For each literal, read its fields and raise an independent finding for each missing field from `ReadTimeout`, `WriteTimeout`, `ReadHeaderTimeout`, `IdleTimeout`. Cite the struct-literal file:line. Also flag `http.ListenAndServe(` calls, which create an implicit zero-value http.Server with no timeouts.
- **DefaultClient / package-level shortcuts**: `grep -En 'http\.Get|http\.Post|http\.Head|http\.DefaultClient' <changed non-test .go files>`. Each hit is a zero-timeout call; a dead upstream blocks the goroutine indefinitely.
- **http.Client zero-timeout**: `grep -n 'http\.Client{' <changed non-test .go files>`. For each literal without a `Timeout:` field, flag it. Downgrade to advisory only if the literal's `Transport` field supplies both `ResponseHeaderTimeout` and `TLSHandshakeTimeout`.
- **http.Transport pool ceiling**: `grep -n 'http\.Transport{' <changed non-test .go files>`. Flag any literal where `MaxIdleConnsPerHost` is absent and `DisableKeepAlives` is not `true`. The stdlib default is 2 idle conns per host; silent TCP-connection churn begins under modest concurrency.
- **Unbounded body read**: `grep -En 'io\.ReadAll|io\.Copy|\.Decode(' <changed non-test .go files in handlers receiving *http.Request>`. If no `http.MaxBytesReader` call wraps `r.Body` before the read in the same handler scope, flag it; a crafted large body causes unbounded allocation.

## Blocking bar
Set `blocking:true` (cite file:line and the grep match or struct field list) ONLY for:
- `http.Server` literal or `http.ListenAndServe` call missing `ReadTimeout` or `WriteTimeout`; either omission allows active-connection goroutines to accumulate without bound under slow clients.
- `http.Get` / `http.Post` / `http.Head` / `http.DefaultClient` in non-test production code; no timeout is enforced on the dialer or response, so the goroutine hangs on a dead upstream.
- `io.ReadAll` / `io.Copy` / `.Decode(` on `r.Body` inside an HTTP handler with no `http.MaxBytesReader` guard; enables OOM via a crafted request.
Everything else is advisory: missing `ReadHeaderTimeout` or `IdleTimeout` alone; `http.Client` without `Timeout` when the transport covers `ResponseHeaderTimeout`; `MaxIdleConnsPerHost` absent (performance risk, not correctness). A finding with no evidence is advisory by rule.

## Anti-patterns to hunt
- `http.Server{}` with no timeout fields — the zero-value server has no timeouts whatsoever.
- `http.ListenAndServe(addr, handler)` top-level call — constructs an invisible zero-timeout server.
- `http.Get(url)` / `http.Post(url, ct, body)` / `http.Head(url)` outside test files.
- `http.DefaultClient.Do(req)` or `http.DefaultTransport` used for production requests.
- `&http.Client{}` with no `Timeout` field and no custom `Transport` supplying per-phase timeouts.
- `&http.Transport{}` with no `ResponseHeaderTimeout`, `TLSHandshakeTimeout`, or `MaxIdleConnsPerHost`.
- `io.ReadAll(r.Body)` or `json.NewDecoder(r.Body).Decode(...)` in a handler before `http.MaxBytesReader`.
- `http.MaxBytesReader` called AFTER the read begins.
- Setting only `http.Server.Addr` and `http.Server.Handler` with no timeout fields — appears intentional but is missing all four timeout knobs.
- `http.Handle` / `http.HandleFunc` registering routes on the default mux paired with `http.ListenAndServe` — the implicit zero-timeout server plus the global default mux is a double hazard.

## Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-http-safety-juror.json, ran[]/skipped[] honest, id = gohttp-<check>-<file>:<line>, nothing outside the JSON.
