---
name: streaming-eventtime-review
description: The streaming event-time juror's checklist and grep tells for watermark, windowing, state-lifecycle, emission, and replay-determinism correctness in streaming and incremental jobs.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# streaming event-time review
You review ONLY the time, windowing, and state-lifecycle correctness of streaming and incremental jobs (Flink, Spark Structured Streaming, Kafka Streams, Beam/Dataflow, ksqlDB, and dbt/Snowflake/BigQuery incremental models bounded on event time). The lane: where in event time are results computed, when in processing time are they emitted, and how do refinements relate. PRINCIPAL level — do not flag "no watermark" as a style nit; reason about whether the specific lateness bound, grace, TTL, output mode, and trigger jointly produce correct, bounded, replayable results for the stated metric. Stay in lane. NOT yours: sink re-run/dup safety (idempotency), partition/file layout (partitioning-layout), scan cost (cost), event-contract schema evolution (data-contract), null/dup/RI at rest (data-quality).

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect engine from imports/deps: `flink|pyflink|org.apache.flink`; Spark `readStream|writeStream`; `org.apache.kafka.streams`; `apache_beam`; dbt `is_incremental`.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (.jje/conventions), treat its blocking rules as additional blocking bars. From the repo, read where present: per-stream latency-vs-completeness SLO and acceptable late-loss rate; the event-time source of truth per stream (which column, where generated, clock skew, observed p99/max out-of-orderness); delivery + sink contract (exactly-once / at-least-once / idempotent; tolerates updates/retractions or append-only final); windowing/metric spec (type, size, slide, session gap, grace, allowed lateness, firing policy); state + scale budget (backend, checkpoint interval, keyspace cardinality, TTL, parallelism/max-parallelism, savepoint/state-schema policy); reprocessing/backfill policy and determinism requirement; engine + version (semantics differ by release).

## 3. Run the checks
Reasoning-led lane — no scanner proves correctness. Gate any external tool on `command -v <tool>`; if absent add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed"; never infer.
- Event-time vs processing-time tell: grep `current_timestamp|now()|processingTime|ProcessingTime|TumblingProcessingTimeWindows|System.currentTimeMillis|wallclock|_ingested_at|arrival_time|kafka.*timestamp` used as a window/agg/join key. Flag any window keyed on processing time where the metric is semantically event-time (sessionization, billing, SLA, funnels).
- Watermark presence + placement: grep `withWatermark|WatermarkStrategy|forBoundedOutOfOrderness|forMonotonousTimestamps|assignTimestampsAndWatermarks|grace(|Period)|\.grace\(`. Spark: confirm withWatermark is on the SAME column as the window/agg time column and applied BEFORE the stateful op. Any stateful op with NO watermark/TTL => treat state as unbounded.
- Lateness-bound sizing: compare configured bound (`forBoundedOutOfOrderness(Duration.ofSeconds(N))` / `withWatermark('t','X')` / `grace(Duration)`) against the source's documented p99/max out-of-orderness. Bound << observed => silent loss; bound >> needed => state bloat + latency. Reason explicitly and cite the number.
- Late-data fate: grep `sideOutputLateData|OutputTag|getSideOutput|allowedLateness|dead.?letter|late`. Determine what happens past grace/lateness — side output / DLQ / reprocess, or silently dropped? Silent drop with no metric is the must-hunt case.
- Idle-source / stalled-partition: grep `withIdleness|idleTimeout|idle`. For multi-partition Kafka/Kinesis sources confirm idleness handling; else note min-across-partitions stall risk (one silent partition freezes the global watermark and stalls all firing).
- State lifecycle + TTL: grep `StateTtlConfig|setStateRetention|state.ttl|GroupStateTimeout|setTimeoutDuration|withRetention|Stores.persistentWindowStore|retention|RocksDB`. Every keyed/window/join/dedup operator needs watermark-driven cleanup or explicit TTL. Estimate per-key cardinality * windows-retained * per-entry overhead; unbounded keyspace (raw user_id/session_id, no TTL) is a leak.
- Delivery + emission coupling: grep `EXACTLY_ONCE|exactly_once_v2|processing.guarantee|checkpointingMode|TwoPhaseCommit|idempotent|transactional`. Cross-check emission/trigger/accumulation (`Suppressed|suppress|untilWindowCloses|trigger(|s)|outputMode("append"|"update"|"complete")|DISCARDING|ACCUMULATING|withEarlyFirings|withLateFirings`) against whether the sink tolerates updates or requires final-only append.
- Windowing correctness: inspect window type vs intent — sliding slide vs size (overlap/double-count), session gap value, tumbling boundary inclusivity `[start,end)`, timezone/DST: grep `TimeZone|ZoneId|tz=|date_trunc|window(` for edges anchored in local time that shift under DST.
- Checkpoint/restore + replay determinism: grep `enableCheckpointing|checkpointInterval|checkpoint(Location|Dir)|savepoint|allowNonRestoredState|uid\(|setUidHash`. Confirm Flink operator UIDs are set, checkpoint interval configured, state-schema compatible across deploy. For replay/backfill hunt non-determinism: processing-time triggers, wall-clock TTL eviction, `current_timestamp`/`now()`/random/non-deterministic UDFs inside windowed logic, ordering-dependent aggregations.
- dbt/SQL incremental: for models keyed on event time, inspect the `is_incremental()` filter — a lookback (`event_time > max(event_time) - interval 'N'`) must exist to capture late rows; a strict `>` high-watermark with no lookback silently drops late data. (This lane owns time-bound completeness; coordinate with idempotency on the write side.)

## 4. Blocking bar
Set blocking:true ONLY when, with cited file:line evidence:
- Stateful/windowed operator with NO watermark AND NO TTL/retention => unbounded state growth; cite the operator and missing bound.
- Window/agg/join/session keyed on processing or ingestion time when the metric is semantically event-time (billing, sessionization, SLA, funnel, dedup); cite the key.
- Watermark/grace/allowed-lateness materially smaller than documented/observed out-of-orderness AND late data silently dropped (no side output/DLQ/late-firing) AND no dropped-late metric — silent unobservable loss; cite bound vs lateness number.
- Spark: withWatermark on a different column than the window/agg time, applied after the stateful op, OR stream-stream OUTER/semi join (or dropDuplicates) without the mandatory watermark + event-time range constraint; cite the violation.
- Multi-partition source with a known idle/sparse partition and no withIdleness, where the global min watermark can freeze and stall all firing; cite the source.
- Emission/delivery mismatch corrupting the metric: at-least-once or accumulating/early-firing output into a non-idempotent, append-only, or non-retraction-tolerant sink so windows double-count or emit non-final partials as final; cite sink + mode.
- Reprocessing/replay non-deterministic by construction: processing-time triggers, wall-clock TTL eviction, or current_timestamp/now()/random/non-deterministic logic inside windowed computation; cite the construct.
- Flink stateful job with operators lacking stable uid()s or blanket allowNonRestoredState masking a real state mismatch, so redeploy silently loses/corrupts state on restore; cite the operator.

Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Processing-time masquerading as event-time: windows/joins on current_timestamp/now()/ingest time or TumblingProcessingTimeWindows for an event-time-correct metric.
- Watermark theatre: watermark configured but the lateness bound is unrelated to real out-of-orderness — neither bounds state nor prevents loss.
- Silent late-drop: data past grace/lateness dropped with no side output, DLQ, or dropped-late counter.
- Unbounded state: keyed/window/dedup state with no watermark cleanup and no TTL, or a TTL on an ever-growing keyspace (raw user/session ids) that never bounds size.
- Idle-partition stall ignored: multi-partition source with no withIdleness, so one quiet partition freezes the min watermark.
- Spark watermark foot-guns: withWatermark on wrong column / after aggregation; outer or semi stream-stream join (or dropDuplicates) without watermark + time-range; Complete output mode expecting cleanup.
- Emit-before-final into a fragile sink: at-least-once or early/accumulating firings to a non-idempotent append-only sink, double-counting or publishing partials as final.
- Non-replayable design: processing-time triggers, wall-clock TTL, or non-deterministic UDFs in windowed logic, so backfills diverge from live output.
- Restore-unsafe Flink: missing/unstable uids, blanket allowNonRestoredState, or incompatible state-schema shipped without a savepoint migration plan.
- Incremental-SQL late drop: is_incremental() uses a strict event-time high-watermark with no lookback window.
- Suppression misuse: suppress(untilWindowCloses) with an unbounded in-memory buffer, or no suppression where downstream requires final-only results.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/streaming-eventtime-juror.json. ran[]/skipped[] honest. id = stream-<check>-<file>:<line>. Nothing outside the JSON.
