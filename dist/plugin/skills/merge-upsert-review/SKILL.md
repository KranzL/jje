---
name: merge-upsert-review
description: The merge-upsert juror's checklist for MERGE INTO, UPDATE, and DELETE DML correctness on Delta Lake, Iceberg, and Hudi tables.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# merge upsert review
You review ONLY SQL DML correctness for MERGE INTO, UPDATE, and DELETE operations on Delta Lake, Iceberg, and Hudi tables: join predicate safety, source dedup, delete-file accumulation, and soft-delete hygiene. PRINCIPAL level. Stay in lane: table format commit validity belongs to table-format; partition design belongs to partitioning-layout; query cost belongs to cost.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect SQL/DML files, dbt models, PySpark scripts, and pipeline DAG files. Grep for `MERGE\b`, `WHEN MATCHED`, `WHEN NOT MATCHED`, `DELETE FROM`, `UPDATE\b` to identify DML targets. Note table format from `_delta_log/`, Iceberg `metadata.json`, or `hoodie.properties` where present.

## 2. Context to load
- Read partition spec (DDL `PARTITIONED BY`, Delta `partitionColumns`, Iceberg partition spec) for every target table touched by the diff.
- Read any scheduled job files (Airflow DAGs, dbt jobs, notebook schedules) to determine whether compaction or OPTIMIZE tasks are already wired for each affected table.
- Note whether the source relation in each MERGE is named as incremental, full-refresh, or unspecified.

## 3. Run the checks (no external linter exists for this lane; reason over SQL and pipeline code; gate any Bash tool on `command -v`; absent -> skipped[] + one info finding)
- **Source dedup**: grep each `MERGE INTO` for its source subquery or CTE. Confirm the source is deduplicated on the join key via `ROW_NUMBER() OVER (PARTITION BY <key>)`, `QUALIFY` (where QUALIFY is supported), or a `DISTINCT` projection covering all join columns. Multiple source rows per join key produce undefined multi-match behavior on Delta and Iceberg — the engine may apply any matching branch. Flag any MERGE source lacking explicit dedup on the full ON-predicate key set.
- **WHEN NOT MATCHED BY SOURCE on partial source**: grep `WHEN NOT MATCHED BY SOURCE` (a Delta Lake MERGE clause). Determine whether the source is a full replica of the target population or a bounded feed (date-filtered CTE, Kafka micro-batch, named incremental dataset). A bounded source combined with this clause deletes every target row absent from the batch. Flag any such occurrence.
- **Iceberg equality-delete accumulation**: grep `write.delete.mode` for `merge-on-read`. Each upsert appends an equality-delete file; without a scheduled `CALL <catalog>.system.rewrite_data_files` (equality-delete rewrite or full compaction), read amplification grows with every batch. Flag a `merge-on-read` table that has no confirmed compaction job in the diff or referenced DAG files.
- **Soft-delete without physical removal**: grep `is_deleted`, `deleted_at`, `_is_deleted`. Tombstoned rows must be physically removed by a scheduled MERGE, Delta `OPTIMIZE`, or Iceberg `rewrite_data_files` that excludes them. Flag a soft-delete pattern with no accompanying removal job in the diff or codebase.
- **Unguarded DELETE**: grep `DELETE FROM`. No WHERE clause — flag immediately (accidental full-table delete).

## Blocking bar
Set `blocking: true` (cite file:line and the exact SQL clause) ONLY for:
- A MERGE whose source subquery or CTE is not deduplicated on the full join key — multi-match produces silent data corruption; behavior is undefined per Delta Lake and Iceberg specs.
- `WHEN NOT MATCHED BY SOURCE` on a demonstrably partial or incremental source — deletes all target rows absent from the batch.
- `DELETE FROM <table>` with no WHERE clause — accidental full-table delete.
Everything else is advisory: equality-delete accumulation where compaction absence is unconfirmed; soft-delete without proven missing removal job; unguarded DELETE on a small or staging table. A finding with no evidence is advisory by rule.

## Anti-patterns to hunt
- MERGE source CTE or subquery without `ROW_NUMBER() OVER (PARTITION BY <key>)` or `QUALIFY` (where QUALIFY is supported) dedup — multi-row fan-out corrupts target rows silently.
- `WHEN NOT MATCHED BY SOURCE` combined with a date-filtered or offset-bounded source.
- `write.delete.mode = 'merge-on-read'` with no `rewrite_data_files` job — equality-delete files accumulate per batch without bound.
- `is_deleted = true` / `deleted_at IS NOT NULL` rows that are never compacted out — table grows without bound, every scan pays tombstone overhead.
- `DELETE FROM tbl` without a WHERE clause — accidental full-table delete.

## Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to `iterations/iter-<n>/verdicts/merge-upsert-juror.json`. `ran[]`/`skipped[]` honest. `id = merge-<check>-<file>:<line>`. Nothing outside the JSON.
