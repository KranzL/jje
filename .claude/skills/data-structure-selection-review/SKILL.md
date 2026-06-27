---
name: data-structure-selection-review
description: The data-structure-selection juror's checklist and grep/EXPLAIN tells for container, sketch, index, and engine fit to access pattern, volume, and exactness — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Data-structure-selection review

You review ONLY the structure-selection decision and its complexity/error consequences — container/algorithm fit to the dominant operation, probabilistic/sketch error models, exact-vs-approximate, mergeability, index/engine fit, cache locality, and immutable-vs-mutable. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Stay in lane: not file encoding/compression (storage-format), table/partition layout (table-format, partitioning-layout), schema evolution (data-contract), null/dup constraints (data-quality), or retry/write-path safety (idempotency).

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect lane artifacts: Python/Java/Go/Scala source on hot paths, notebooks `.ipynb`, SQL/dbt models, streaming/aggregation jobs (Spark/Flink/Beam), feature definitions, and store/engine config. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from `.jje/conventions`), treat its blocking rules as additional blocking bars. From the spec's `context_needed`, find and read where present: the access-pattern + SLA spec (dominant op, read:write ratio, latency/throughput budget, concurrency model); data-volume/cardinality estimates (N now and projected, distinct keys, key-space boundedness, skew); the metric layer / metric contracts (which metrics are exact-required vs approximation-tolerant); error-budget conventions; the OLTP/OLAP/serving engines and their available index/sketch types; the streaming framework and whether per-shard merge happens; feature-store online/offline serving topology and lookup budget; runtime/memory model (GC, container ceiling, hot vs warm); and the approved sketch/concurrent-structure library list. Without access-pattern + N you cannot judge fit — say so rather than guess.

## 3. Run the checks (gate any external tool on `command -v`; missing -> `skipped[]` + one info finding; never infer)
Most of this lane is reasoning-led. Identify the dominant access pattern FIRST (point lookup / range / membership / top-k / cardinality / frequency / quantile / similarity), then test the chosen structure against THAT at the stated N.
- Linear membership on the hot path: grep `\bin \[`, `in list(`, `\.index(`, list `.contains(`/`indexOf`, Go `slices.Contains`/range loops. Confirm it runs inside a loop over data (O(n*m)) where a set/dict/HashSet is O(1).
- Accidental quadratic: grep `\.append(` on DataFrames, `pd.concat`/`np.append` inside loops, `iterrows`/`itertuples` for vectorizable work, list build-and-search per iteration, string `+` concat in loops. O(n^2), blocking at scale.
- SQL plans: where a DB is reachable, `EXPLAIN`/`EXPLAIN ANALYZE` and read it. Tells: `Seq Scan` on a large table with a selective predicate, `Nested Loop` over large inputs needing `Hash Join`, sort+limit unable to use an index for top-k, bitmap thrash. Check index type vs predicate: hash index with range/`BETWEEN`/`ORDER BY` (needs B-tree), B-tree on boolean/low-cardinality (partial/BRIN), `LIKE '%x'`/array/jsonb containment without GIN.
- Exact-vs-approximate audit: grep `COUNT(DISTINCT`, `PERCENTILE_CONT`, `PERCENTILE_DISC`, `MEDIAN`, `NTILE`, `APPROX_*`. Cross-reference the metric layer and verify the DIRECTION: exact required for billing/regulatory/money-dedup/fraud/safety; APPROX (HLL / t-digest / DDSketch) is the principled choice for high-cardinality dashboard/monitoring/capacity metrics.
- Probabilistic sizing: grep `BloomFilter`/`bloom`, `CuckooFilter`, `HyperLogLog`/`HLL`/`hll_`, `CountMinSketch`/`cms`, `TDigest`/`DDSketch`, `MinHash`/`LSH`. Confirm params are sized against REAL expected N — Bloom ~9.6 bits/element at 1% FPR, k≈(m/n)ln2; HLL std error ~1.04/sqrt(2^p); Count-Min width=e/epsilon, depth=ln(1/delta). Hard-coded/guessed params or unbounded structures are findings.
- Error-direction safety: a Bloom/Cuckoo positive is uncertain (false positives, no false negatives); inspect what action a positive gates — "filter says already paid -> skip payment" drops real work. Count-Min only over-estimates; flag it where an under-safe bound is needed.
- Deletion/TTL: grep `.remove(`/`.delete(` and sliding-window semantics near a plain Bloom/HLL (neither supports deletion) — needs Cuckoo/counting-Bloom or a windowed/rotating sketch.
- Mergeability: grep `reduce`, `combine`, `merge`, `union`, `treeAggregate` near a per-shard structure. Safe: HLL union, t-digest/DDSketch merge, Count-Min add. Red flags: summing per-shard exact `COUNT(DISTINCT)`, averaging per-shard percentiles, merging mismatched-precision HLLs, biased reservoir merge.
- Top-k: grep `sort`/`sorted`/`ORDER BY ... LIMIT k`/`argsort` then taking first k. If k << n on a hot path, a bounded heap (`heapq.nlargest`, size-k `PriorityQueue`) is O(n log k) vs O(n log n) — flag the full sort.
- LSM vs B-tree (RUM): check read:write ratio against the engine — write-heavy ingest on a B-tree (write amplification) or latency-critical point reads on LSM without bloom/block-cache (read/space amplification) is a mismatch.
- Cache locality: array-of-structs / list-of-dicts / boxed numerics / pointer-chasing iterated in a numeric hot loop where columnar/primitive SoA (numpy/arrow) is cache- and SIMD-friendly.
- Immutable vs mutable: grep `copy.deepcopy`/`clone()`/defensive full copies in hot loops (want persistent/structurally-shared), AND shared mutable module-level/default-arg collections mutated across threads/tasks without synchronization or copy-on-write.
- Similarity/dedup: grep nested loops computing pairwise `jaccard`/`cosine`/distance (O(n^2)). At large n needs MinHash+LSH or an ANN index (HNSW/IVF), not brute force.
- Rationale: confirm an ADR/comment/design note states access pattern, N, and why this structure/error budget. Absence is advisory; for a probabilistic structure gating a real decision, absence of a sized error budget is blocking.

## 4. Blocking bar
Set `blocking: true` only for:
- An approximate/probabilistic structure (HLL/APPROX_COUNT_DISTINCT, Count-Min, t-digest/APPROX_QUANTILE, Bloom dedup, sampling) produces a number the metric layer marks exact-required (billing, revenue, regulatory, money dedup, fraud, safety) with no documented sign-off.
- A one-sided structure gates a decision in the unsafe direction: a Bloom/Cuckoo positive treated as authoritative where a false positive drops/skips real work, or a Count-Min over-estimate used where an under-safe bound is required.
- A hot/production path has the wrong asymptotic complexity for the documented volume and will miss SLA or OOM/timeout: O(n) membership in a loop, accidental O(n^2), full sort for tiny-k over huge n, brute-force O(n^2) pairwise similarity, or an unindexed Seq Scan/Nested Loop on the critical query path at stated scale.
- A probabilistic structure with NO error budget tied to reality: FPR/precision/width hard-coded or guessed, not linked to a downstream tolerance — including unbounded-growth structures (Bloom needing deletes, Count-Min/HLL over an unbounded key space with no rotation/decay) that degrade past spec over time.
- A per-shard structure combined non-mergeably yielding biased results: summed exact distincts, averaged percentiles, mismatched-precision sketch merge, or a merge with no associative operation.
- Index/engine choice contradicts the dominant access pattern causing scans/amplification on the critical path at stated load (engine/index selection, not partition layout).
- Deletion/retraction/TTL required by semantics but the structure cannot support it (plain Bloom/HLL), producing accumulating false positives or stale membership.
- A shared mutable structure read/written across threads/tasks/partitions without synchronization, copy-on-write, or an immutable alternative on a real-concurrency path.
Everything else is advisory: a correct-but-suboptimal structure, missing ADR where the choice is acceptable, hand-rolled structure where a vetted library exists, over-provisioned precision, defensive copies on a warm path, a mildly-better specialized container. A finding with no evidence (grep line / plan node / reproducing N) is advisory by rule.

## 5. Anti-patterns to hunt
- Linear scan for membership (`x in list`, `.contains`, `.indexOf`, repeated `.index()`) inside a loop where a set/dict/hash is O(1).
- Accidental quadratic: `df.append`/`pd.concat`/`np.append` in loops, `iterrows`/`itertuples` for vectorizable work, build-and-search per iteration, string concat in loops.
- Exact `COUNT(DISTINCT)`/`PERCENTILE_CONT` over huge high-cardinality dashboard/monitoring data where a sized HLL/t-digest meets budget — and the inverse, an APPROX_* feeding a billing/regulatory/money-dedup metric that requires exact.
- Probabilistic structure with magic-number params (Bloom FPR, HLL precision, Count-Min width/depth) with no derivation from real cardinality and no downstream-tolerance link.
- Treating a Bloom/Cuckoo positive (or any one-sided estimate) as authoritative in the unsafe direction.
- Plain Bloom/HLL where deletion/sliding-window/TTL is required (needs Cuckoo, counting-Bloom, or windowed/rotating sketch).
- Non-mergeable cross-shard combination: summing per-shard distincts, averaging percentiles, merging mismatched-precision sketches, reducing a no-unbiased-merge structure.
- Full sort to take top-k where k << n; brute-force O(n^2) pairwise similarity/dedup where MinHash+LSH or an ANN index is required.
- Wrong index for the predicate (hash for ranges/ordering, B-tree on boolean, missing GIN for jsonb/array/full-text); wrong engine for the read:write ratio (LSM for latency-critical point reads without mitigation, B-tree under heavy ingest).
- Pointer-chasing AoS / list-of-objects / boxed numerics in a numeric hot loop where columnar/primitive SoA is cache- and SIMD-friendly.
- Defensive deepcopy in a hot path instead of a persistent/shared immutable structure; shared mutable structure mutated across threads/tasks without synchronization.
- Unbounded structure with no rotation/decay whose error grows silently past spec.
- Re-deriving exact data on every access (rebuilding a set/index per call) instead of building it once for repeated lookups.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/data-structure-selection-juror.json`. `id` = `dsfit-<check>-<file>:<line>`. `ran[]`/`skipped[]` honest (gate every external tool on `command -v`; a DB/EXPLAIN you could not run goes in `skipped[]`). Nothing outside the JSON.
