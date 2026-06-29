---
name: streaming-eventtime-review
description: The streaming event-time juror's checklist and grep tells for watermark, windowing, state-lifecycle, emission, and replay-determinism correctness in streaming and incremental jobs.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# streaming event-time review
You review ONLY the time, windowing, and state-lifecycle correctness of streaming and incremental jobs (Flink, Spark Structured Streaming, Kafka Streams, Beam/Dataflow, ksqlDB, and dbt/Snowflake/BigQuery incremental models bounded on event time). Lane: WHAT data (window), WHERE in event time, WHEN in processing time (trigger), HOW refinements relate (accumulation: DISCARDING/ACCUMULATING/ACCUMULATING_AND_RETRACTING — Akidau et al., VLDB 2015). PRINCIPAL level. NOT yours: sink re-run/dup safety (idempotency), partition/file layout (partitioning-layout), scan cost (cost), schema evolution (data-contract), null/dup/RI at rest (data-quality).

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect engine from imports/deps: `flink|pyflink|org.apache.flink`; Spark `readStream|writeStream`; `org.apache.kafka.streams`; `apache_beam`; dbt `is_incremental`.

## 2. Reference specs
- **Dataflow Model** (Akidau et al., VLDB 2015): canonical trigger taxonomy (AfterWatermark, AfterPane (count-based), AfterProcessingTime, AfterAny/AfterAll composites) and accumulation modes (DISCARDING, ACCUMULATING, ACCUMULATING_AND_RETRACTING); all Flink/Beam/Spark Structured Streaming event-time semantics descend from this model.
- **Flink state backends**: HashMapStateBackend (heap — OOM on unbounded keyspace); RocksDBStateBackend (off-heap — large/unbounded state, spill to disk). Backend determines failure mode; check `state.backend` config alongside keyspace analysis.
- **Spark Structured Streaming** (Armbrust et al., SIGMOD 2018): `withWatermark` must precede the stateful op on the same time column; stream-stream OUTER/semi join requires watermark + event-time range constraint; inner join requires watermark to bound state; `dropDuplicates` requires watermark.

## 3. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane, treat its blocking rules as additional blocking bars. Read where present: per-stream latency/completeness SLO and acceptable late-loss rate; event-time source of truth per stream (column, p99/max out-of-orderness, clock skew); sink contract (exactly-once / at-least-once; tolerates updates/retractions); windowing spec (type, size, slide, gap, grace, trigger, accumulation mode); state budget (backend, checkpoint interval, keyspace cardinality, TTL, parallelism); reprocessing/backfill policy; engine + version.

## 4. Run the checks
Gate any external tool on `command -v`; absent → skipped[] + one info finding; never infer.
- **Event-time vs processing-time**: grep `current_timestamp|now()|processingTime|ProcessingTime|TumblingProcessingTimeWindows|System.currentTimeMillis|_ingested_at|arrival_time` as window/agg/join key. Flag any window keyed on processing time where the metric is semantically event-time.
- **Watermark presence + placement**: grep `withWatermark|WatermarkStrategy|forBoundedOutOfOrderness|forMonotonousTimestamps|assignTimestampsAndWatermarks|grace\(|\.grace\(`. Spark: confirm same column as agg key, applied BEFORE the stateful op. Any stateful op with no watermark/TTL => unbounded state.
- **Lateness-bound sizing**: compare configured bound against p99 out-of-orderness from context-load. Blocking requires all three: bound < p99 AND no side output/DLQ/late-firing AND no dropped-late counter. If p99 is unknown the finding is advisory by default for lack of evidence.
- **Late-data fate**: grep `sideOutputLateData|OutputTag|getSideOutput|allowedLateness|dead.?letter|late`. Determine fate past grace — side output/DLQ/reprocess, or silently dropped with no metric.
- **Idle-source / stalled-partition**: grep `withIdleness|idleTimeout|idle`. Blocking only when a known idle/sparse partition exists AND no `withIdleness` AND the frozen min watermark demonstrably impacts a latency/completeness SLO; else advisory.
- **State lifecycle + TTL**: grep `StateTtlConfig|state.ttl|GroupStateTimeout|setTimeoutDuration|withRetention|Stores.persistentWindowStore`. Every keyed/window/join/dedup op needs watermark-driven cleanup or explicit TTL. Keyspace > ~1M distinct live keys with no TTL is blocking; note backend (HashMapStateBackend → OOM, RocksDB → disk blowup).
- **Delivery + emission coupling**: grep `EXACTLY_ONCE|exactly_once_v2|processing.guarantee|TwoPhaseCommit`. Cross-check accumulation/trigger (`Suppressed|suppress|untilWindowCloses|outputMode|DISCARDING|ACCUMULATING|withEarlyFirings|withLateFirings`) against whether the sink tolerates updates or requires final-only append.
- **Multi-stream join watermark dominance**: grep `join.*stream|stream.*join|StreamJoin|coGroup`. Join output is gated by the SLOWEST watermark across all joined streams; compare lateness bounds across each stream and cite the dominant one.
- **KStream/KTable temporal confusion**: grep `KTable.*join|GlobalKTable`. A KTable join uses the latest committed value per key — equivalent to a naive latest-value join. Blocking when the joined dimension is time-varying and no event-time range constraint scopes the join to the correct as-of window.
- **Windowing correctness**: sliding slide vs size (overlap/double-count), session gap value, tumbling boundary `[start,end)`, DST: grep `TimeZone|ZoneId|tz=|date_trunc|window(` for local-time-anchored edges that shift under DST.
- **Checkpoint + replay determinism**: grep `enableCheckpointing|checkpointInterval|uid\(|setUidHash|allowNonRestoredState|savepoint`. Confirm Flink operator UIDs set; checkpoint interval ≤ recovery SLO. Hunt non-determinism: processing-time triggers, wall-clock TTL eviction, `current_timestamp`/`now()`/random/non-deterministic UDFs inside windowed logic.
- **dbt/SQL incremental**: `is_incremental()` filter must include a lookback (`event_time > max(event_time) - interval 'N'`); strict `>` high-watermark with no lookback silently drops late rows.

## 5. Blocking bar
Set blocking:true ONLY when, with cited file:line evidence:
- Stateful/windowed op with NO watermark AND NO TTL/retention => unbounded state growth; cite the operator.
- Window/agg/join/session keyed on processing or ingestion time when the metric is semantically event-time (billing, sessionization, SLA, funnel, dedup).
- Lateness bound < p99 observed out-of-orderness AND no side output/DLQ/late-firing AND no dropped-late metric (all three conditions required).
- Spark: `withWatermark` on wrong column or applied after the stateful op; stream-stream OUTER/semi join or `dropDuplicates` without watermark + event-time range constraint.
- Keyspace > ~1M distinct live keys with no TTL and no watermark cleanup, OR unbounded keyspace (raw user_id/session_id) with no TTL.
- Multi-partition source with a known idle/sparse partition, no `withIdleness`, and the frozen watermark demonstrably stalls SLO-bound firing.
- Emission/delivery mismatch: accumulating or early-firing output into an append-only or non-retraction-tolerant sink, causing double-counting or partial-as-final publication.
- KTable/GlobalKTable join on a time-varying dimension with no as-of event-time range constraint (naive latest-value join).
- Replay non-deterministic by construction: processing-time triggers, wall-clock TTL eviction, or `current_timestamp`/`now()`/random inside windowed computation.
- Flink stateful job: operators missing stable `uid()`s, or blanket `allowNonRestoredState` masking a real state mismatch.

Advisory (do not escalate to blocking): checkpoint interval within 2× window slide but within recovery SLO; lateness bound > p99 but below observed maximum with late data in a monitored side output; idle-source stall risk where all partitions are known high-volume; RocksDB with large but TTL-bounded state; watermark bound generously large causing state bloat but no correctness loss. Everything else is advisory. A finding with no evidence is advisory by rule.

## 6. Anti-patterns to hunt
- Processing-time masquerading as event-time: windows/joins on `current_timestamp`/`now()`/ingest time or `TumblingProcessingTimeWindows` for a semantic event-time metric.
- Watermark theatre: bound configured but unrelated to real out-of-orderness — neither bounds state nor prevents loss.
- Silent late-drop: data past grace/lateness dropped with no side output, DLQ, or dropped-late counter.
- Unbounded state: keyed/window/dedup state with no watermark cleanup and no TTL, or TTL on an ever-growing keyspace (raw user/session ids).
- Idle-partition stall ignored: multi-partition source with no `withIdleness`, one quiet partition freezing the min watermark.
- Spark watermark foot-guns: `withWatermark` on wrong column or after aggregation; outer/semi stream-stream join or `dropDuplicates` without watermark + time-range; Complete output mode expecting cleanup.
- Emit-before-final into a fragile sink: early/accumulating firings to an append-only or non-retraction-tolerant sink.
- Non-replayable design: processing-time triggers, wall-clock TTL, or non-deterministic UDFs in windowed logic.
- Restore-unsafe Flink: missing/unstable `uid()`s, blanket `allowNonRestoredState`, incompatible state-schema without a savepoint migration plan.
- Incremental-SQL late drop: `is_incremental()` strict event-time high-watermark with no lookback window.
- KStream/KTable temporal confusion: `KTable.join()`/`GlobalKTable.join()` on a time-varying dimension with no as-of range constraint.
- Multi-stream join latency dominance: mismatched lateness bounds on joined streams — slowest bound governs all output latency.

## 7. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/streaming-eventtime-juror.json. ran[]/skipped[] honest. id = stream-<check>-<file>:<line>. Nothing outside the JSON.
