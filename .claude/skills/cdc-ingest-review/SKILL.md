---
name: cdc-ingest-review
description: The CDC-ingest juror's checklist for source-sequence ordering, write-side dedup, transaction-boundary collapsing, PK-change decomposition, tombstone handling, and schema-change propagation in Debezium/Kafka-Connect/Airbyte/Fivetran pipelines landing into Delta/Iceberg/Hudi.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# CDC ingest review
You review ONLY CDC source-to-lakehouse write correctness: event ordering by source sequence, write-side dedup, transaction-boundary collapsing, PK-change decomposition, tombstone handling, and schema-change propagation for Debezium, Kafka Connect, Airbyte, and Fivetran pipelines landing into Delta/Iceberg/Hudi. Stay in lane: watermark/late-data/event-time window semantics belong to streaming-eventtime; file format, partitioning, and query cost belong to their respective jurors.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect CDC artifacts in CHANGED: Debezium connector JSON/YAML, Kafka consumer code, Airbyte/Fivetran connector config, Spark/Flink/Python sink code referencing `_op`, `before`, `after`, `lsn`, `seq`, `__deleted`, or `tombstone`, and SQL MERGE/upsert statements. Review only those files.

## 2. CDC envelope reference
Debezium `op`: `c`=insert, `u`=update, `d`=delete, `r`=snapshot-read. `source` carries `lsn` (Postgres), `pos`/`file` (MySQL binlog), `scn` (Oracle). Tombstone = Kafka record with non-null key and null value, emitted after the delete event when `tombstones.on.delete=true`. Airbyte exposes `_ab_cdc_deleted_at` and `_ab_cdc_updated_at`; Fivetran uses `_fivetran_deleted` and `_fivetran_synced`. These field names anchor every grep below.

## 3. Run the checks
No dedicated CDC static-analysis linter exists; all checks are grep-based reasoning over connector config and pipeline logic. Gate `jq` on `command -v jq`; absent → skipped[] + one info finding.

- **LSN/sequence ordering**: grep `lsn|seq|scn|pos|source\.sequence` in sink code. Flag pipelines that apply CDC events to the lakehouse with no `ORDER BY`/sort on the source sequence field before the MERGE/write — out-of-order application produces wrong final row state with no error.
- **Write-side dedup on (PK, sequence)**: grep `MERGE|upsert|COPY INTO|foreachBatch|writeStream`. Flag sinks with no dedup keyed on `(primary_key, lsn|seq|offset)` before or inside the write. At-least-once CDC delivery guarantees duplicate events will arrive under normal operation.
- **Transaction-boundary collapsing**: grep `transaction_id|txId|transaction\.id` in CDC processing code. Flag pipelines that process individual CDC events without grouping same-PK operations within one source transaction to the final committed state — intermediate states must not land as separate rows.
- **PK change decomposition**: grep `UPDATE.*SET.*\bpk\b\|op.*u.*before\b` and inspect MERGE/upsert logic. Flag any CDC handler that applies a PK-column mutation as a single UPDATE rather than decomposing to DELETE(old_pk) then INSERT(new_pk) — most lakehouse MERGE implementations silently corrupt rows on PK mutations.
- **Tombstone handling**: grep `filter.*null\|tombstone\|_deleted.*false` in Kafka consumer code. Flag any consumer that discards null-value tombstone records from log-compacted topics — these are the hard-delete signal and must reach the lakehouse sink.
- **Schema-change event handling**: grep `SchemaChangeEvent\|include\.schema\.changes\|schemaEvolution\|DDL` in pipeline code and connector config. Flag pipelines with no branch or handler for Debezium DDL events or Airbyte schema-change signals — unhandled schema changes silently corrupt subsequent rows.

If `command -v jq`, parse Debezium connector JSON for `tombstones.on.delete`, `include.schema.changes`, and `offset.storage` settings and surface misconfigurations alongside code findings.

## 4. Blocking bar
Set blocking:true (cite file:line) ONLY for:
- No sort/de-conflict on source sequence/LSN before lakehouse write — produces wrong final row state.
- No dedup on (PK, sequence|lsn|offset) in MERGE/upsert sink — produces silent duplicate rows under at-least-once delivery.
- No transaction-boundary collapsing on same-PK events within one source transaction — intermediate states land as rows.
- PK-column mutation applied as a single UPDATE in a lakehouse MERGE path — wrong data after PK changes.
- Kafka consumer filters or discards null-value tombstone records from a log-compacted topic — hard deletes not propagated to the lakehouse.
- No schema-change event handler for a Debezium or Airbyte pipeline — silent row corruption on upstream DDL.
Everything else is advisory: no ordering on a staging-only non-serving landing table; dedup on PK alone without sequence; tombstone handling deferred to a downstream compaction job with a documented SLA; schema-change alerting only with a manual runbook. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `filter(record.value() != null)` on a log-compacted topic — tombstones discarded, hard deletes lost.
- `MERGE ... WHEN MATCHED THEN UPDATE SET pk_col = new_val` — PK mutation as UPDATE, not DELETE+INSERT.
- `writeStream`/`foreachBatch` with no `dropDuplicates` or window-dedup keyed on `(pk, lsn|seq|offset)` before write.
- CDC event loop with no `ORDER BY lsn`/`ORDER BY seq` or sequence-keyed sort before the lakehouse write.
- `transaction_id` present in the CDC envelope but not used to collapse same-PK operations before the sink.
- `include.schema.changes=false` in Debezium connector config with no out-of-band DDL handler.
- `tombstones.on.delete=false` in Debezium connector config — source never emits the tombstone record.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/cdc-ingest-juror.json, ran[]/skipped[] honest, id = cdc-<check>-<file>:<line>, nothing outside the JSON.
