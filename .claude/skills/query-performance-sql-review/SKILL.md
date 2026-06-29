---
name: query-performance-sql-review
description: The query-performance-sql juror's checklist and exact commands for the per-query execution plan and SQL authorship — join execution, pushdown, sargability/pruning defeats, window/CTE efficiency, spill, and skew.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# query performance sql review
You review ONLY the per-query execution PLAN and the SQL authorship that produces it: join execution (hash/sort-merge/nested-loop, order, build-vs-probe, broadcast-vs-shuffle), predicate/projection pushdown, query-side pruning defeats (sargability), plan-shape anti-patterns, window efficiency, CTE materialization, spill, and skew. PRINCIPAL level — hold the bar at what a principal would BLOCK, not surface lint. NOT physical layout (partitioning-layout juror), NOT total scanned bytes / warehouse sizing (cost juror), NOT file/column encoding (storage-format juror). Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only changed SQL: dbt/SQL models (.sql), notebooks (.ipynb), and inline query strings. For dbt, find the rendered SQL under target/compiled — never EXPLAIN the templated source.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. From the repo, load what this lane needs: target ENGINE + major version (PG 11 vs 12+, Spark 3.x AQE on/off, Snowflake, BigQuery, Redshift, Trino, DuckDB, ClickHouse) — join names, CTE materialization semantics, and plan vocabulary all differ; the index/sort-key/cluster-key/dist-key catalog for touched tables; approximate cardinalities and which tables are "large/fact" vs "small/dim"; stats-freshness convention; the metric/semantic layer (dbt + MetricFlow, LookML) to know which CTEs/models are reused downstream; engine resource config that moves plan thresholds (work_mem/hash_mem_multiplier, `spark.sql.adaptive.*`/`autoBroadcastJoinThreshold`, warehouse size); whether the PR convention requires an attached EXPLAIN/profile; acceptable fan-out tolerance and known-skewed keys (null FKs, hot tenant_ids, sentinels).

## 3. Run the checks (gate each external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
Get a REAL plan on the changed, rendered SQL. dbt: `dbt compile` then read target/compiled. PG: `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT) <sql>`; for fleet-level identification of expensive queries query `pg_stat_statements` (calls, shared_blks_hit/read). Redshift: `EXPLAIN [VERBOSE] <sql>`. Spark: `df.explain('formatted')` or `EXPLAIN FORMATTED`/`EXPLAIN COST`. Snowflake: `EXPLAIN USING TEXT` plus `QUERY_HISTORY`. BigQuery: `INFORMATION_SCHEMA.JOBS_BY_PROJECT` (`total_slot_ms`) post-execution. Trino: `EXPLAIN ANALYZE`. If no engine is reachable, fall back to static reasoning and SAY SO.
- Join nodes: flag `Nested Loop` whose inner AND outer actual rows are both > 10K each (no index on the inner key); flag a build/hash side that is the BIGGER relation (Hash rows > probe rows); in Spark flag `SortMergeJoin`/`ShuffleHashJoin` where one side is small enough for `BroadcastHashJoin` (below `spark.sql.autoBroadcastJoinThreshold`, default 10 MB), and the reverse — a broadcast of a side above that threshold risking driver OOM.
- Estimate-vs-actual: in EXPLAIN ANALYZE compare `rows=` (estimated) to `actual rows`; a >10x gap at a scan or join is the tell for stale stats or a non-sargable predicate — drive the finding from it, not a guess. For PG, confirm stats currency with `SELECT n_mod_since_analyze FROM pg_stat_user_tables WHERE relname='<table>'`; for correlated-column cardinality errors (PG 10+), `CREATE STATISTICS` is the fix.- Sargability greps on WHERE/ON/JOIN of changed SQL: `grep -niE '(where|and|on|join).*(date|cast|upper|lower|substr|left|coalesce|trunc|to_char|date_trunc)\s*\(' $CHANGED` (function wrapping a column); `grep -nE '::[a-z]' $CHANGED` and `grep -niE 'cast\s*\(' $CHANGED` (casts on the column side / implicit-cast join keys); `grep -niE "like\s*'%" $CHANGED` (leading-wildcard LIKE). In the plan look for `CONVERT_IMPLICIT` (Redshift), high `Rows Removed by Filter`, or `Filter:` where an `Index Cond:` was expected.
- Pushdown: confirm filters appear as `Index Cond`/`Recheck`/partition-pruned scan (PG `never executed` subplans, BigQuery pruned partitions, Spark `PushedFilters`/`PartitionFilters`) rather than a `Filter` above a join; flag projection not pushed (full-width scan feeding a narrow output) — tie to `SELECT *`: `grep -nE 'SELECT[[:space:]]+\*' $CHANGED`.
- Correlated-subquery / fan-out: `grep -niE 'where exists|where.*in[[:space:]]*\(select|= *\(select' $CHANGED` (correlated scalar/EXISTS — candidate semi-join or window rewrite); `grep -niE 'select[[:space:]]+distinct' $CHANGED` and GROUP BY over all output columns right after a join (fan-out crutch — verify the join grain).
- OR-defeating-index: `grep -niE '\bor\b' $CHANGED` inside WHERE across different columns; confirm the plan produced a full scan (not `BitmapOr`/index union); recommend UNION ALL or rewrite.
- Window efficiency: list every window — `grep -niE 'over[[:space:]]*\(' $CHANGED`; flag multiple windows with differing PARTITION BY/ORDER BY forcing extra `Sort`/`WindowAgg`; flag `RANGE BETWEEN` where `ROWS` was intended (peer-group double counting); flag manual `ROW_NUMBER()=1` dedupe where `QUALIFY` is supported.
- CTE materialization: count references to each `WITH x AS` name. BigQuery always materializes CTEs (no inlining). Spark always inlines (no MATERIALIZED keyword). PG12+ inlines by default but honors MATERIALIZED. A multi-reference CTE on a large input under an inlining engine (Spark, PG12+) should be materialized/temp; a single-reference PG MATERIALIZED fence that blocks predicate pushdown into a large scan should be inlined; flag recursive CTEs without a clear termination bound.
- Spill and skew: PG `Sort Method: external merge  Disk:` and `Batches: >1`/`temp written` on Hash; Spark stage `spill (memory/disk)` and task max-duration/rows >> median; BigQuery stage compute `max` >> `avg` (skew) or shuffle bytes spilled to disk. Confirm `spark.sql.adaptive.skewJoin.enabled` before blocking on skew the platform would auto-heal (`spark.sql.adaptive.skewJoin.skewedPartitionFactor` default 5, `skewedPartitionThresholdInBytes` default 256 MB define the trigger boundary).

## 4. Blocking bar
Set blocking:true ONLY with plan/predicate evidence cited:
- A join executes as a NESTED LOOP over two large inputs (both sides > 10K actual rows, no index on the inner key), or a CROSS JOIN / unintended cartesian fan-out from a missing/incomplete ON predicate — quadratic blow-up confirmed in the plan.
- A predicate defeats index/partition/cluster pruning the query was meant to use — a function or implicit cast on the KEY column, a type-mismatched join key forcing CONVERT_IMPLICIT (Redshift), or a leading-wildcard LIKE — AND the plan shows a full scan / unpruned partitions. Cite the predicate and the scan line.
- A filter/join key that should prune partitions is wrapped/transformed so all partitions scan (e.g. `WHERE DATE(event_ts)=...` on a ts-partitioned table) — query-authorship pruning defeat.
- Broadcast/shuffle misjoin in MPP/Spark with evidence: a large->small join shuffled (sort-merge) when broadcast was correct AND it causes confirmed shuffle spill, OR a broadcast of a side above `spark.sql.autoBroadcastJoinThreshold` (default 10 MB) risking driver/exec OOM.
- Confirmed disk SPILL on the hot path that a bounded fix removes (external-merge sort or multi-batch hash to disk in PG, Spark stage disk-spill, BigQuery shuffle to disk) where a sargable predicate, projection pushdown, pre-aggregation, or repartition keeps it in memory.
- Severe, unhandled data SKEW on the hot path (Spark skewed task max >> median — AQE auto-heals at skewedPartitionFactor >= 5x or partition > 256 MB; BigQuery stage compute-max >> avg) on a key the authors know is hot, with AQE skew-join NOT enabled and no salting/handling.
- DISTINCT or GROUP-BY-all used to hide a fan-out join (the join grain is wrong) — correctness-adjacent: the dedupe masks row multiplication and scans/sorts the inflated set.
- A multiply-referenced CTE/subquery recomputed N times on a large input where materializing once is the fix, or a single-use CTE fence that demonstrably blocks predicate pushdown into a large scan — with the plan showing the repeated/blocked scan.
Everything else is advisory: a >10x estimate/actual gap where statistics are fresh (stats staleness is a DBA concern, not a PR blocker); ORDER BY without LIMIT on a large intermediate with no confirmed spill; UNION where UNION ALL would suffice but no plan evidence of the sort-dedup cost; a CTE materialization fence that is correct but pushdown-limiting to future edits; mild window redundancy with no plan evidence of extra sorts. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Function or cast on an indexed/partition/sort/cluster key in WHERE/ON (`DATE(ts)`, `CAST(id AS text)`, `col::text`, `UPPER(col)`, `col+0`, `COALESCE(col,x)`) — non-sargable, defeats pruning.
- Implicit type-mismatch on a join/filter key (int column = '123' literal, varchar join to int) forcing CONVERT_IMPLICIT (Redshift) and a scan.
- Leading-wildcard `LIKE '%term'` (or LIKE on a function-wrapped column) where an index/search path existed.
- OR across different columns in WHERE forcing a full scan instead of an index union / UNION ALL.
- Nested-loop / cartesian fan-out from a missing or partial join key (accidental cross join).
- DISTINCT or GROUP-BY-all-columns deduping a fan-out join instead of fixing the join grain (DISTINCT-as-crutch).
- Correlated scalar/EXISTS subquery in SELECT/WHERE re-executing per outer row where a semi-join or window aggregate is correct.
- `SELECT *` feeding a join/window/CTE/aggregate, defeating projection pushdown and widening shuffle.
- Multiply-referenced CTE recomputed each reference instead of materialized once; or a single-use CTE fence blocking predicate pushdown.
- Inconsistent PARTITION BY/ORDER BY across windows causing redundant sort/window passes; RANGE frame where ROWS was intended.
- Build/hash side of a hash join is the larger relation; or a shuffle/sort-merge join where one side was broadcast-eligible (and vice-versa, broadcasting an oversized side).
- Ignoring confirmed disk spill or known key skew on the hot path with no sargable predicate, repartition, salting, or AQE skew-join enabled.
- Trusting estimated cost without reading EXPLAIN ANALYZE actuals — shipping a >10x estimate-vs-actual row divergence unaddressed.
- `ORDER BY` / unbounded sort with no LIMIT or no supporting order on a large intermediate, materializing and sorting the full set.
- `NOT IN (SELECT col ...)` when col is nullable — three-valued logic silently returns zero rows (NULL anti-join trap). Grep: `grep -niE 'not\s+in\s*\(\s*select' $CHANGED`; then confirm column nullability.
- `UNION` (dedup + sort) where `UNION ALL` was intended — forces a full sort+distinct over the union result. Grep: `grep -nE '\bUNION\b' $CHANGED` excluding UNION ALL lines.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/query-performance-sql-juror.json. ran[]/skipped[] honest. id = `qperf-<check>-<file>:<line>`. Nothing outside the JSON.
