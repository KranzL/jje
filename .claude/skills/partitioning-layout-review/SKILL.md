---
name: partitioning-layout-review
description: The partitioning-layout juror's checklist and exact commands for partition design, small-files, file/row-group sizing, compaction, and clustering.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# partitioning layout review
You review ONLY the datalake physical layout: partition key design, small-files, file/row-group sizing, compaction, and clustering/Z-order. Stay in lane: format codec/encoding belongs to storage-format; query cost to cost; schema evolution to data-contract.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles/config (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml, delta log, iceberg metadata).

## 2. Context to load
Detect the table engine from the diff: Delta (`_delta_log`), Iceberg (`metadata.json`, `write.format.default`), Hudi (`.hoodie`), or Hive DDL (`STORED AS`/`USING`). Read any DDL and compaction-schedule files in $CHANGED. Engine determines which target-file-size property and partition-count limits apply below.

## 3. Reference numbers
- **Spark**: `spark.sql.files.maxPartitionBytes` default 134217728 bytes (128MB); `spark.sql.adaptive.coalescePartitions.enabled` merges small post-shuffle files when AQE is active.
- **Delta**: ZORDER practical limit ~4 columns beyond which locality gains diminish.
- **Iceberg**: `write.target-file-size-bytes` default 536870912 (512MB); hidden-partition transforms (identity/bucket/truncate/year/month/day/hour) replace Hive-style `PARTITIONED BY` and avoid partition-key exposure.
- **Hudi**: `hoodie.parquet.max.file.size`; `hoodie.compaction.strategy`; `hoodie.cleaner.policy` required on MOR tables.
- **HMS-backed engines**: Hive Metastore degrades noticeably above ~100K partitions.

## 4. Run the checks
Gate every external tool on `command -v`; absent → skipped[] + one info finding. Reason over DDL and write/job config:
- **Partition cardinality**: `grep -niE 'PARTITIONED BY|partitionBy|partition_by' $CHANGED` — flag keys with > ~50K distinct values (user_id, raw timestamp, UUID) → small-files explosion. Date/hour grain or bucket/truncate transform is standard.
- **Partition count ceiling**: estimate post-write count; flag > ~100K for HMS-backed engines (metastore degradation).
- **Predicate alignment**: confirm partition columns appear in documented query WHERE predicates; no alignment → no pruning benefit.
- **Compaction strategy**: `grep -niE 'OPTIMIZE|compaction|vacuum|hoodie\.compaction|hoodie\.cleaner' $CHANGED` — streaming/append tables must declare a strategy; absence is a defect.
- **File sizing config**: `grep -niE 'maxRecordsPerFile|target.file.size|write\.target-file-size-bytes|hoodie\.parquet\.max\.file\.size|optimize\.maxFileSize|maxPartitionBytes' $CHANGED` — values producing files consistently < 16MB are a small-files defect.
- **Clustering/Z-order**: `grep -niE 'ZORDER|clusterBy|bucketBy|CLUSTER BY' $CHANGED` — ZORDER on > ~4 columns loses locality; bucket columns must align with documented join keys.
- **Overwrite mode**: `grep -niE 'partitionOverwriteMode|insertOverwrite|overwriteSchema' $CHANGED` — `spark.sql.sources.partitionOverwriteMode=static` (the Spark default) rewrites the entire table on every append to a partitioned sink; `dynamic` is correct for incremental loads.

## 5. Blocking bar
Set blocking:true (cite config file:line and the specific engine limit) ONLY for:
- Partition key with > ~50K distinct values and no bucketing/transform to normalize cardinality → small-files explosion, scan amplification on every query.
- Post-write partition count exceeding a hard engine ceiling: > ~100K for HMS-backed engines (metastore degradation).
- Streaming or high-frequency append table with no compaction/OPTIMIZE strategy → unbounded small-files accumulation.
- `spark.sql.sources.partitionOverwriteMode` absent or set to `static` on a partitioned sink receiving incremental appends → full-table rewrite on every run.
- Partition scheme with demonstrably no query pruning (partition columns absent from WHERE clauses in any DDL, view, or query file in $CHANGED) on a table > ~1GB.
Everything else is advisory: suboptimal ZORDER column count; file sizes modestly below target on small/staging tables; choice between valid Hudi compaction strategies. A finding with no evidence is advisory by rule.

## 6. Anti-patterns to hunt
- `coalesce(1)` / `repartition(1)` on a large table → single-file output, kills all write parallelism.
- Nested/redundant partition columns: `PARTITIONED BY (year, date)` where `date` subsumes `year` → doubled partition count for no additional pruning.
- Null-value partition explosion: a nullable partition column creates `__HIVE_DEFAULT_PARTITION__` that accumulates unboundedly as bad rows arrive.
- `spark.sql.sources.partitionOverwriteMode=static` (or absent) on an incremental append job → silently rewrites the entire table every run.
- ZORDER on > ~4 columns — locality gains diminish and OPTIMIZE runtime grows with no query benefit.
- Partition key on a raw timestamp or UUID column — effectively one partition per row, the canonical small-files explosion.
- `OPTIMIZE` without a `WHERE` clause on a large Delta table → full-table rewrite instead of recently-written dirty files only.
- No `hoodie.cleaner.policy` on a Hudi MOR table — delta logs accumulate unboundedly, read amplification grows without bound.

## 7. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/partitioning-layout-juror.json. ran[]/skipped[] honest. id = part-<check>-<file>:<line>. Nothing outside the JSON.
