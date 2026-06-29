---
name: idempotency-review
description: The idempotency juror's checklist and exact grep patterns for reasoning over write-path re-run/retry safety.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

# idempotency review
You review ONLY write semantics: whether a re-run or retry duplicates or corrupts data. Six steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Context to load
Before reasoning, establish: (a) the upstream delivery guarantee — at-least-once or at-most-once (pipeline contract, Kafka consumer-group config, Structured Streaming trigger); (b) the primary/partition key schema for every changed table (DDL, schema registry, dbt model YAML); (c) the retry policy and whether a dead-letter queue exists; (d) for dbt: `unique_key` and `incremental_strategy` (merge/delete+insert/append) from `dbt_project.yml` or model config; (e) whether the write path spans services and lacks a dedup guard. Without (a)–(b) the MERGE-key and watermark checks cannot be completed.

## 3. Run the checks
Grep: `MERGE`, `INSERT`, `INSERT OVERWRITE`, `\.mode\(["']append["']\)`, `upsert`, `ON CONFLICT`, `dedup`, `distinct`, `watermark`, `unique_key`, `enable\.idempotence`, `foreachBatch`.

- **MERGE/upsert key**: the `ON` predicate must uniquely identify a row — a nullable column, auto-increment surrogate, or mutable attribute in the predicate fans out on re-run. Cite the ON clause and the column DDL.
- **Append vs overwrite**: Spark `.mode("append")` re-runs duplicate rows; safe only with an upstream dedup guard. The idempotent re-run pattern is `.mode("overwrite")` with `spark.sql.sources.partitionOverwriteMode=dynamic` plus a partition column. `INSERT OVERWRITE` must cover the whole target partition.
- **Dedup logic**: `DISTINCT` / `ROW_NUMBER() OVER (PARTITION BY <natural_key> ORDER BY ...)` present and filtering to `rn=1`? Surrogate-key dedup without the natural key is wrong.
- **Watermark**: correct pattern is `WHERE event_ts > :hwm AND event_ts <= :new_hwm` with the new HWM committed atomically after the write succeeds. Advancing HWM before commit drops records on retry.
- **dbt incremental**: `unique_key` must be defined for `incremental_strategy: merge` or `delete+insert`; `append` strategy is non-idempotent by default — flag unless an upstream dedup exists. (dbt Core incremental model docs.)
- **Kafka/Structured Streaming**: when the upstream delivers at-least-once, making the write path idempotent requires `enable.idempotence=true` on any re-producing Kafka producer plus a transactional consumer or idempotent sink (Kafka KIP-98 exactly-once transactional API). A `foreachBatch` sink with no dedup or transaction enrollment is unguarded.
- **External API calls**: a payment, notification, or mutable-state call inside a retry-able write path (Spark `foreachBatch`, Flink process function) must carry an idempotency-key header scoped to the source message/batch offset; absence on a non-idempotent endpoint is blocking.
- **Write-then-swap**: the safe pattern is write to a temp path then atomic rename/swap; a direct overwrite of the live path is a partial-overwrite hazard. Flag writes to the final path without an intermediate staging step.

Gate every external tool on `command -v`; absent tool → skipped[] + one info finding.

## 4. Blocking bar
Set blocking:true (cite file:line and the key/clause) ONLY for:
- Spark `.mode("append")` to a previously-written path with no dedup guard — cite the `.mode()` call and target path.
- `TRUNCATE` + `INSERT` not inside a single explicit transaction (`BEGIN`/`COMMIT` or equivalent) — cite the `TRUNCATE` statement and the absent transaction boundary.
- `MERGE` / `UPSERT` predicate includes a nullable, auto-increment, or mutable column — cite the `ON` clause and the column DDL.
- `INSERT INTO` without `ON CONFLICT` in Postgres-dialect SQL on a table with a unique constraint where re-run will duplicate rows — cite the insert and the constraint.
- dbt incremental model with `incremental_strategy: merge` or `delete+insert` and no `unique_key` defined — cite the model config block.
- External API call (payment, notification, mutable state) in a retry-able write path with no idempotency key — cite the call site and delivery guarantee.
- Kafka consumer / Structured Streaming `foreachBatch` under at-least-once delivery with no dedup or KIP-98 transactional enrollment — cite the sink code.
- Direct overwrite of the live path without an atomic write-then-rename for a non-table-format write — cite the write statement and path.
Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `\.mode\(["']append["']\)` to the same target path on retry with no dedup guard.
- `TRUNCATE` followed by `INSERT` with no enclosing `BEGIN`/`COMMIT` — failure between the two leaves the table empty.
- `CREATE TABLE` without `OR REPLACE` or `IF NOT EXISTS` in DDL executed on every run.
- `MERGE` / `UPSERT` `ON` clause using a nullable column, an auto-increment surrogate, or any mutable attribute.
- `INSERT INTO` without `ON CONFLICT` in Postgres-dialect SQL where the target has a unique constraint.
- dbt `incremental_strategy: append` with no upstream dedup — every backfill or full-refresh duplicates the partition.
- `foreachBatch` / Flink process function calling a non-idempotent external endpoint with no idempotency-key header.
- HWM advanced before the downstream write commits — failure between advance and write silently drops records.
- An incremental/backfill window with no overlap dedup or partition isolation — re-running or overlapping a date range double-counts the boundary rows.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/idempotency-juror.json. ran[]/skipped[] honest. id = idem-<check>-<file>:<line>. Nothing outside the JSON.
