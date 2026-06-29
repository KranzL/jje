---
name: table-format-review
description: The table-format juror's checklist and exact commands — schema evolution, partition-spec evolution, snapshot/time-travel, and ACID commit semantics across Iceberg, Delta Lake, and Hudi.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Table format review

You review ONLY the lakehouse table format surface: schema evolution, partition-spec evolution, snapshot/time-travel, and ACID/commit semantics across Iceberg, Delta Lake, and Hudi. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect format: `_delta_log` → Delta Lake; `metadata/*.metadata.json` or `USING iceberg` → Iceberg; `.hoodie/` → Hudi. Review only `$CHANGED` and what they touch.

## 2. Spec anchors
- **Iceberg Table Spec** (iceberg.apache.org/spec): allowed type promotions — `int→long`, `float→double`, decimal precision widening (scale must not change). Hard rejections: `long→int`, any decimal scale change, `string→int`. v1/v2 boundary: v2 tables carry equality/position delete files; v1-only readers silently skip them, producing wrong results without error.
- **Delta Protocol** (delta-io/delta PROTOCOL.md): rename/drop without column-mapping = drop+add (null backfill on pre-mapping files, data loss). Column mapping requires `minReaderVersion=2, minWriterVersion=5`. Deletion vectors require `minReaderVersion=3, minWriterVersion=7`. These bumps break any reader below that version.
- **Avro Schema Resolution** (avro.apache.org/docs/current/spec.html#Schema+Resolution): governs Hudi type compat at read time; backward-incompatible changes (`int→string`, decimal precision decrease) cause read failures on existing files.
- **Hudi**: `hoodie.table.type` (CoW vs MoR) is immutable after creation; in-place change is explicitly unsupported and leaves the table in an undefined state.

## 3. Run the checks
Gate any CLI on `command -v`; absent → `skipped[]` + one `info`. Reason statically over DDL, `metadata.json`, `_delta_log`, `.hoodie/` timeline, and config.

**Schema evolution** — grep `ALTER TABLE`, `mergeSchema`, `hoodie.datasource.write.reconcile.schema`:
- Iceberg: verify each column change against the allowed-promotions list; rename/drop is safe only via field-id reassignment.
- Delta: rename/drop without `delta.columnMapping.mode` in the protocol entry = drop+add → null backfill on old files.
- Hudi: apply Avro backward-compat rules; `int→string`, precision decrease → read failures on existing files.
- `mergeSchema=true` on any Spark/Delta write silently widens schema each run; grep for it.

**Partition-spec evolution** — grep `PARTITION BY`, `partitionSpec`, `hoodie.datasource.hive_sync.partition_fields`:
- Iceberg: in-place evolution is safe (new spec applies to new files only; old files retain old spec).
- Delta/Hudi: in-place change requires a full table rewrite; without it, reads are data-corrupting.

**Atomicity** — verify every write lands in a commit log:
- Delta: data files in the table path with no corresponding `_delta_log/N.json` entry; partitioned overwrite without `replaceWhere`.
- Iceberg: files under `data/` with no `metadata/version-hint.text` pointer swap.
- Hudi: data files with no matching entry in `.hoodie/` timeline.
- Grep `TRUNCATE`, `INSERT OVERWRITE`, `overwrite` not wrapped in a transaction.

**Snapshot lifecycle** — grep `VACUUM`, `ExpireSnapshots`, `hoodie.cleaner.commits.retained`:
- Delta: `delta.deletedFileRetentionDuration` default 7 days; flag if set below the required replay window.
- Iceberg: `history.expire.max-snapshot-age-ms` default 432000000 ms (5 days); flag `ExpireSnapshots` calls below the replay window.
- Hudi: `hoodie.cleaner.commits.retained` default 10; flag if below the required replay window.

## 4. Blocking bar
Set `blocking: true` (cite spec + file:line) ONLY for:
1. Any Iceberg type narrowing or scale change (`long→int`, decimal scale change) — Iceberg Table Spec allowed-promotions list.
2. Rename/drop on Delta without `columnMapping.mode` + `minReaderVersion=2/minWriterVersion=5` — null backfill and data loss on pre-mapping files.
3. Iceberg v2 equality/position deletes on a `format-version: 1` table — v1 readers silently skip delete files, wrong results without error.
4. Non-atomic write: data files with no matching commit-log entry (per-format tells above).
5. `hoodie.table.type` changed on an existing table — explicitly unsupported, undefined table state.
6. Hudi type change failing Avro backward compatibility — read failures on existing files.
7. Delta `columnMapping.mode` enabled without `minReaderVersion=2/minWriterVersion=5`, or deletion vectors enabled without `minReaderVersion=3/minWriterVersion=7` — silent reader breakage.
8. In-place partition-spec change on Delta or Hudi without full table rewrite.
Everything else is advisory (`warn`/`info`, `blocking: false`). A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `TRUNCATE + INSERT` or `INSERT OVERWRITE` replacing an atomic `MERGE`/`REPLACE INTO` — exposes a non-atomic window to live readers.
- Partitioned Delta overwrite without `replaceWhere` — overwrites the entire table instead of the target partition.
- `delta.columnMapping.mode` set without `minReaderVersion=2, minWriterVersion=5` protocol bump.
- `hoodie.table.type` change (CoW↔MoR) on an existing table.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/table-format-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`. `id` = `tfmt-<check>-<file>:<line>`. Nothing
outside the JSON.
