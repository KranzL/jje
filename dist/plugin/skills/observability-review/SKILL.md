---
name: observability-review
description: The observability juror's checklist and exact grep patterns for logging, metrics, tracing, and error-path coverage on new code paths.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

# observability review
You review ONLY the observability surface: logging, metrics, tracing, and error-path coverage on NEW code paths. PRINCIPAL level. Stay in lane: SLO budget/alert routing and infrastructure resource sizing belong to other lanes.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Reference canon
- **RED Method** (Tom Wilkie, Weaveworks): every new request-driven surface must expose Rate (request counter), Errors (error counter or span error status), and Duration (histogram — not a gauge or plain counter). All three are required.
- **USE Method** (Brendan Gregg): background jobs and resource-consuming workers must track Utilization, Saturation, and Errors.
- **OpenTelemetry Semantic Conventions** (opentelemetry.io/docs/specs/semconv): span status must be set to `StatusCode.ERROR` with a description on every error path; leaving it `Unset`/`OK` makes error-rate dashboards silently wrong.
- **W3C TraceContext Recommendation**: distributed services must propagate `traceparent`/`tracestate` headers across all outbound HTTP calls; absence breaks distributed traces at the call boundary.
- **Prometheus data model**: histograms emit `_bucket`/`_sum`/`_count` suffixes; metric labels must never carry user-controlled or request-scoped values (user_id, request_id, raw URL path) — high-cardinality labels are a production incident vector causing metrics-store degradation under real traffic.

## 3. Run the checks
For each NEW surface in $CHANGED (request handler, background job, outbound call), verify error-path instrumentation and RED/USE coverage. Use ecosystem-aware patterns keyed to the detected lockfile:
- Go: `grep -nE 'slog\.|zap\.|logrus\.|zerolog\.'` (logging); `grep -nE 'otel\.Tracer|span\.SetStatus|span\.RecordError'` (tracing); `grep -nE 'prometheus\.New(Counter|Histogram|Gauge)|MustRegister'` (metrics).
- Python: `grep -nE 'structlog|loguru|logging\.(error|warning|exception)'` (logging); `grep -nE 'opentelemetry\.trace\.get_tracer|span\.set_status|StatusCode'` (tracing); `grep -nE 'prometheus_client|Counter|Histogram'` (metrics).
- Node: `grep -nE 'pino|winston|logger\.(error|warn)'` (logging); `grep -nE '@opentelemetry/api|span\.setStatus|SpanStatusCode'` (tracing); `grep -nE 'prom-client|new Counter|new Histogram'` (metrics).

Then check:
- **Span status**: on every error path, confirm `span.SetStatus`/`set_status`/`setStatus` sets `StatusCode.ERROR`; flag any span whose status stays `Unset` or `OK` after an error is caught or returned.
- **Structured logging**: flag string-concatenation log calls (`Printf("%s %v", ..., err)`, f-strings or template literals inside log args) — they break log query tooling and risk log injection; require key-value or JSON structured emission.
- **Trace propagation through async boundaries**: grep goroutine spawns (`go func`, `go f(`), queue publishes (Kafka/SQS/Pub-Sub send), and async/await entry points; flag where `ctx` is not forwarded or where `propagator.Inject`/`Extract` is absent on outbound calls.
- **Duration metric type**: for any new latency metric, confirm it is a histogram type — not a gauge or plain counter — P50/P99 cannot be derived without histogram buckets.

Gate any external tool on `command -v`; absent → skipped[] + one info/non-blocking finding. Never infer.

## 4. Blocking bar
Set blocking:true (cite file:line) ONLY for:
- A NEW handler, job, or outbound call with a reachable error path that has no log at ERROR/WARN level capturing the error value — silent failure is invisible in production.
- A span emitted on a path ending in error whose status is left `Unset`/`OK` (violates OTel Semantic Conventions span-status requirement) — error-rate dashboards read zero while errors occur.
- A new Prometheus or OTel metric label whose value is user-controlled or request-scoped (user_id, request_id, session_id, raw URL path) — cardinality explosion degrades the metrics store under load.
- A new distributed service outbound call with no `traceparent`/`tracestate` propagation (W3C TraceContext) — breaks the distributed trace entirely at the call boundary.

Everything else is advisory: partial RED coverage on an existing surface; missing USE metrics on an unchanged background job; histogram bucket boundaries not tuned to SLO targets; structured logging not adopted in files untouched by this change; trace context gaps in unchanged code. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Silent `catch`/`except`/`recover` block with no log — the error is swallowed and invisible to all tooling.
- Span created on an error path with status left `Unset` or `StatusCode.OK` — error-rate metric reads zero while failures occur.
- High-cardinality label values on Prometheus/OTel metrics: user_id, request_id, session_id, or a raw URL path as a label value — cardinality explosion under real traffic.
- Trace context not forwarded through goroutine spawns, queue publishes/consumes, or async/await hand-offs — the distributed trace is severed at the async boundary.
- Unstructured log emission via string concatenation or `%s`-formatted error values instead of key-value pairs or structured JSON — breaks log query tooling and risks log injection.
- Duration captured as a gauge or plain counter instead of a histogram — P50/P99 latency cannot be computed; SLO tracking is impossible.
- RED coverage incomplete on a new request-driven surface: Rate present but no Errors counter/span-status, or no Duration histogram.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/observability-juror.json. ran[]/skipped[] honest. id = obs-<check>-<file>:<line>. Nothing outside the JSON.
