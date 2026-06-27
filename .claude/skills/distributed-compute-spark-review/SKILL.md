---
name: distributed-compute-spark-review
description: The distributed-compute-spark juror's checklist and exact commands — predict the Catalyst/AQE physical plan and shuffle behavior of Spark/PySpark/Spark SQL jobs and block constructs that skew, spill, OOM, or serialize the cluster.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# distributed compute (Spark) review
You review ONLY the runtime execution efficiency and stability of distributed-compute jobs on Spark and Spark-compatible dataframe engines (PySpark, Spark SQL, Scala/Java Spark, Databricks/EMR/Glue). You reason about the physical plan, shuffle, join strategy, skew, and memory the code IMPLIES at scale — NOT on-disk layout (partitioning-layout/storage-format/table-format own that) and NOT dollar cost (cost owns that). PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Write findings as predicted-plan reasoning, not generic lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the lane's artifacts in $CHANGED: PySpark/Scala transforms (.py/.scala), Spark SQL, notebooks (.ipynb), DAG/job files, and Spark config (spark-defaults, conf set in code). Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. Read from the repo where present, and weigh the spec's context: Spark/PySpark version and platform (AQE+skewJoin default-on only 3.0/3.2+; vanilla vs Databricks Photon vs EMR vs Glue); cluster/executor shape (memory, cores/executor, count) and spark.memory.fraction; the team's Spark config baseline (spark.sql.shuffle.partitions, adaptive.enabled, autoBroadcastJoinThreshold, adaptive.advisoryPartitionSizeInBytes, adaptive.skewJoin.enabled) — review the delta against baseline, not absolutes; input data scale/growth and documented heavy hitters (e.g. "country=US is 40%", "device_id null ~12%") so skew is provable not speculative; job nature (batch vs Structured Streaming vs interactive); the UDF policy and whether Arrow (spark.sql.execution.arrow.pyspark.enabled) is on; SLA/critical-path; and whether the platform has automatic disk cache (Databricks Delta cache) which makes manual cache() of a Parquet/Delta scan an anti-pattern.

## 3. Run the checks
Gate any external tool on `command -v <tool>`; if absent -> skipped[] + one info finding "check skipped: <tool> not installed". Never infer what an un-run check would have found. Most of this lane is reasoning-led.
- Read the physical plan, do not guess: where runnable, `df.explain('formatted')` / `explain(mode='cost')` / `EXPLAIN FORMATTED` in SQL. Inspect for Exchange (=shuffle) nodes, the join operator (BroadcastHashJoin vs SortMergeJoin vs ShuffledHashJoin vs BroadcastNestedLoopJoin), and AdaptiveSparkPlan isFinalPlan. Count Exchanges — each is a stage boundary and a skew/spill risk.
- Driver-collect footguns: `grep -nE '\.collect\(\)|\.collectAsList\(|\.toPandas\(|\.toLocalIterator\(|\.take\(|\.head\([0-9]{4,}' $CHANGED`. Any unbounded collect of a non-aggregated df is a flag; confirm a LIMIT or proven-small upstream.
- Forced single-partition writes: `grep -nE 'coalesce\(1\)|repartition\(1\)|COALESCE\(1\)' $CHANGED` — almost always a small-files-fix done wrong that single-cores the final stage.
- Broadcast hints / threshold tampering: `grep -nE "hint\('broadcast'\)|broadcast\(|/\*\+ ?BROADCAST|autoBroadcastJoinThreshold" $CHANGED` — trace whether the broadcast side is a bounded small dim or a fact/growing table; flag `=-1` (disables broadcast globally).
- Python UDFs in the hot path: `grep -nE '@udf|[^_]udf\(|spark\.udf\.register' $CHANGED` — check whether the body reimplements a native function (when/coalesce/regexp_replace/date math). Distinguish `@pandas_udf`/`applyInPandas` (vectorized, acceptable). Flag UDFs sitting between a scan and a filter (defeats predicate pushdown).
- Cache/persist hygiene: `grep -nE '\.cache\(\)|\.persist\(|StorageLevel\.' $CHANGED` — trace (a) how many actions consume it, (b) a matching `.unpersist()`, (c) an action after cache() to materialize, (d) whether the relation is a single-use scan.
- Skew-prone keys: `grep -nE 'join\(|groupBy\(|partitionBy\(' $CHANGED` on columns named `*_id` (null-likely), status/country/type/category (low cardinality), or a known-hot date/tenant. Check for null handling (filter isNotNull before join, COALESCE keys, or salting).
- Plan-bloating loops / wide transforms: `grep -nE 'for .*withColumn|\.distinct\(\)|\.dropDuplicates\(|\.orderBy\(|\.sort\(' $CHANGED` — withColumn-in-loop -> one select/selectExpr; full-row dedup vs business-key; global sort = full shuffle.
- Explode fan-out: `grep -nE 'explode\(|explode_outer\(|posexplode\(' $CHANGED` — estimate fan-out factor and whether a repartition precedes it.
- repartition vs coalesce intent: inspect every `.repartition(n)`/`.coalesce(n)` — repartition(col) to fix skew/pre-shuffle parallelism (full shuffle, OK); coalesce only to REDUCE partitions downstream of a filter, never to raise parallelism (it cannot), never directly upstream of a wide stage where it pins a low partition count up the narrow chain.
- Spark UI / event log when available: Stages tab for max task duration / shuffle-spill (disk+memory) >> median (skew tell), Storage tab for cached RDDs never evicted, SQL tab for the plan, GC time >10-15% of task time (= GC pressure), "spilled" bytes in stage metrics.
- Validate AQE actually works: confirm spark.sql.adaptive.enabled true (or platform default), no static repartition(n) immediately preceding a join (pins partitions, blunts coalescePartitions/skewJoin), and skewedPartitionThresholdInBytes/advisoryPartitionSizeInBytes sane vs data scale.
- Partition-sizing math: estimate post-shuffle bytes / spark.sql.shuffle.partitions; target ~64-128MB/partition. Flag oversized (spill/OOM) and tiny (scheduler overhead, small files).

## 4. Blocking bar
Set blocking:true ONLY for (everything else advisory; a finding with no evidence is advisory by rule):
- Unbounded driver collect: collect()/toPandas()/collectAsList()/toLocalIterator() (or display/print of a full df) on a not-provably-bounded df (no LIMIT, not a small aggregate) in a production path — predictable driver OOM.
- Broadcasting an unbounded/growing relation: a BROADCAST hint or broadcast() on the fact/large/over-time-growing side, or raising autoBroadcastJoinThreshold to cover it — driver materialization + executor OOM + broadcastTimeout.
- Untreated provable skew on a join/aggregation/window: keying on a documented heavy-hitter or null-heavy column with no mitigation (no AQE skewJoin applicability, no salting, no null isolation) such that one task gets a multiple of the median and will spill/OOM. Blocking only when demonstrable, not speculative. Note: AQE skewJoin covers sort-merge JOIN skew only — aggregation/window skew still needs salting.
- Forced single-partition compute/write at scale: coalesce(1)/repartition(1)/COALESCE(1) on a large dataset, collapsing the final stage to one core/executor. Blocking unless data is proven tiny.
- Disabling the safety nets without justification: spark.sql.adaptive.enabled=false or autoBroadcastJoinThreshold=-1 globally in a job whose joins depend on them, or a static repartition(n) that pins partition count and defeats AQE coalescing/skew handling on a large shuffle.
- Caching that breaks memory/correctness: caching a large relation MEMORY_ONLY that exceeds storage memory (silent partial cache -> recompute + GC thrash), or persist() with no unpersist() in a long-running/loop job that leaks executor memory. Blocking when it will evict/OOM in the documented cluster shape.
- Row-at-a-time Python UDF on a hot, high-volume path that reimplements an available native pyspark.sql.functions expression (or could be a pandas_udf), placed where it defeats predicate/projection pushdown. Blocking when on the critical path and a native equivalent exists.
- Cartesian / nested-loop blowups: an unintended cross join (missing/implicit condition -> BroadcastNestedLoopJoin/CartesianProduct) or an explode with large fan-out and no repartition.
- Oversized post-shuffle partitions: a wide stage whose estimated partition size is many hundreds of MB to GB (shuffle.partitions far too low) guaranteeing disk spill / executor OOM in the team's executor shape.

## 5. Anti-patterns to hunt
- collect()/toPandas()/collectAsList()/toLocalIterator() of an unbounded df to the driver.
- BROADCAST hint or broadcast() on a large/growing relation; raising autoBroadcastJoinThreshold to force it.
- autoBroadcastJoinThreshold=-1 or adaptive.enabled=false disabling the planner's safety nets without cause.
- Joining/grouping/windowing on a null-heavy or single-hot-value key with no salting/null-isolation/skew handling.
- coalesce(1)/repartition(1) to make one output file (single-cores the stage); using coalesce to try to INCREASE parallelism (it cannot — needs repartition).
- coalesce(n) upstream of a wide transform, pinning a low partition count up the narrow chain and starving the shuffle.
- Row-at-a-time @udf in the hot path reimplementing a native function or that should be a pandas_udf/Arrow vectorized UDF; UDF between scan and filter defeating pushdown.
- cache()/persist() on a single-use or trivially-recomputed df; cache() with no matching unpersist() in a loop/long job; assuming cache() materializes without a following action; MEMORY_ONLY of a set larger than storage memory.
- Static repartition(n) immediately before a join that blunts AQE coalescePartitions/skewJoin.
- Unintended cross join (missing join key -> CartesianProduct/BroadcastNestedLoopJoin); explode with large fan-out and no preceding repartition.
- withColumn in a Python loop / long withColumn chains (logical-plan bloat) instead of one select/selectExpr.
- distinct()/dropDuplicates() on all columns instead of business keys; global orderBy with no downstream need.
- spark.sql.shuffle.partitions so low post-shuffle partitions are GB-sized (guaranteed spill/OOM), or so high it overshuffles tiny data.
- df.count() used purely as an existence/materialization probe, triggering a full shuffle/scan.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/distributed-compute-spark-juror.json. ran[]/skipped[] honest. id = spark-<check>-<file>:<line>. Nothing outside the JSON.
