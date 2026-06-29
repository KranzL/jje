---
name: algorithmic-complexity-review
description: The algorithmic-complexity juror's checklist and grep tells for time/space complexity on hot, data-scaling paths — accidental quadratic, N+1, materialization, fan-out, ReDoS — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Algorithmic complexity review
You review ONLY time and space complexity of code on hot / data-scaling paths — any logic whose cost grows with input size N (rows, events, keys, files, fan-out). PRINCIPAL level — derive the asymptotic class and the constant-factor structure that turns "linear" quadratic in practice; hold the bar at what a principal engineer would block, not a lint. Do not flag "a loop": derive complexity as a function of the real scaling variable, name the concrete triggering input, and state the post-fix O-class. Stay in lane (algorithmic scaling, not scan-bytes or file layout — that is the cost juror).

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect the relevant artifacts: app code (Python/JS/TS/Go/Scala/Java), dbt/SQL models, notebooks (.ipynb), Spark/Flink/Beam jobs, UDFs, feature definitions. Classify each changed unit as hot/scaling (per-row UDF, per-request handler, streaming/micro-batch operator, full-table transform) vs. cold/bounded (one-time migration, backfill, setup over a fixed tiny N) BEFORE judging. O(N^2) over a fixed tiny N is fine.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional blocking bars. From the spec's context_needed, read where present: the scale envelope per dataset/table/endpoint (expected and worst-case N — row counts, key cardinality, explode fan-out F, growth rate; without this "quadratic" cannot be ranked), latency/throughput SLOs and batch size, the compute engine and execution model (Spark/Flink lazy DAG, shuffle, broadcast threshold, AQE; warehouse SQL optimizer/join strategies; pandas/Polars/DuckDB eager-vs-lazy; plain service), the data-access/ORM and feature-store conventions (eager/batched-join mandate, point-lookup vs. batch API), the team's collection idioms (set/dict/hash index, heap top-k, reservoir, HLL/count-min), driver/client memory and partition-size limits and the collect() rule, and the trust boundary on input sizes/regexes/nesting depth. State N explicitly for every finding (e.g. N = rows in fact table, K = distinct keys, F = explode fan-out).

## 3. Run the checks (gate every external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
Mostly reasoning-led. For each changed hot unit, derive the O-class (time AND space) and pass count.
- Nested-loop / accidental-quadratic: `grep -nE 'in \[|\.includes\(|\.indexOf\(|\.contains\(|\.index\('` then verify the container is a list/array rebuilt or scanned each iteration; nested `for`/`while`; `.iterrows()`/`.itertuples()`/`.apply(`; app-side double loop `for a in A: for b in B`.
- Quadratic accumulation: `grep -nE 'pd\.concat|df = df\.append|\.append\(|\+= '` — confirm a growing structure (DataFrame/list/string) is copied O(N) times in a loop -> O(N^2).
- N+1 / repeated work: `grep -nE 'for .*:|\.map\(|\.foreach\('` then look inside for `execute|query|get|fetch|requests\.|client\.|read_|load|open\(`; lazy ORM relations walked in a loop with no `select_related`/`joinedload`/`includes`/prefetch; loop-invariant work (`re.compile`, schema/JSON parse, connection open, sort, full aggregation) done inside the loop instead of hoisted.
- Data-structure selection: membership/dedup/group on a list instead of set/dict/Counter/hash index? Whole dataset sorted/loaded for top-k instead of a bounded heap/`nlargest`? Row-by-row join instead of hash/merge join? (Inverse — heavy machinery for tiny fixed N — advisory only.)
- Streaming vs. materialize: `grep -nE '\.collect\(\)|\.toPandas\(\)|fetchall\(\)|readlines\(\)|list\(.*cursor|\.cache\(\)|\.persist\('` — does an unbounded relation/whole file/partition get pulled into one node's RAM when a single streaming pass / windowed aggregate / bounded heap would do? Count passes over the data (repeated `.groupBy`/`.join`/re-read of the same source).
- Fan-out / cardinality explosion: `grep -nE 'explode|cross *join|CROSS JOIN|cartesian|\.crossJoin|full outer'` and SQL joins missing an `ON`/with non-equi predicates -> derive output cardinality (m*n) and whether dedup/aggregation runs before or after the fan-out. For concurrent fan-out: `grep -nE 'go func|go [a-zA-Z]'` on Go range loops and `grep -nE 'threading\.Thread\('` inside Python for-loops — O(N) goroutines/OS threads where N is unbounded exhausts the scheduler and is treated identically to an unpartitioned Spark task fan-out.
- Spark/SQL-specific: when available read the query plan — `EXPLAIN`/`EXPLAIN ANALYZE` (gate `command -v` on the relevant CLI), Spark UI stage metrics — for sort-merge join on a skewed key, broadcast of a too-large side (`spark.sql.autoBroadcastJoinThreshold` default 10 MB pre-AQE), shuffle on every row, `repartition` thrash, UDFs blocking pushdown. Judge O-class, pass count, and skew worst-case, not scan-bytes.
- Pathological / worst-case: `grep -nE 're\.compile|Pattern\.compile|\(.*[+*]\).*[+*]'` for nested-quantifier/alternation regex on untrusted input (ReDoS / CWE-1333; OWASP: owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS); attacker-controllable recursion/parse depth/width (CWE-407); hash structures keyed on attacker-controlled values (collision DoS — Crosby & Wallach, USENIX Security 2003); join/group keys with known skew. Name the concrete triggering input and the worst-case bound, not the amortized one.
- Ground in evidence where a harness exists: run the benchmark/profiler (`command -v` gate: cProfile/`py-spy`, `async-profiler` for JVM, `EXPLAIN ANALYZE`, Spark UI) and cite measured scaling, or construct the minimal input class (N vs. 10x N) demonstrating super-linear growth. A profiler trace, benchmark delta, or production incident already showing super-linear p99 latency or RSS growth proportional to N is blocking evidence and overrides the "no triggering input = advisory" rule.

## 4. Blocking bar
Set `blocking: true` only when the finding cites file:line (or the plan stage / benchmark delta), names the scaling variable N, and states the resulting AND post-fix complexity. Block for:
- A hot/scaling path with super-linear time (O(N^2), O(N*M) both scaling, O(N*K) per-key rescans, exponential) where N is unbounded or grows with data/traffic AND a concrete triggering input/scale is identified.
- N+1 / per-row external work (query, RPC, feature-store lookup, file open, model load, connection) that executes once per row/element when one batched/joined call would do.
- Materializing an unbounded relation into single-node memory (`collect()`/`toPandas()`/`fetchall()`/whole-file read) on a not-provably-bounded path when a one-pass/streaming/bounded-structure alternative exists — an OOM that is a function of data growth.
- Cardinality-explosion fan-out (cross/cartesian join, join missing its key, `explode` without a downstream bound) making output and downstream stages O(m*n) at scale.
- Worst-case-triggerable pathological behavior across a trust boundary: ReDoS/catastrophic backtracking (CWE-1333), attacker-controllable recursion/parse depth or hash-collision blow-up (CWE-407) — amortized-fine-but-worst-case-DoS counts.
- An algorithm/data-structure choice asymptotically worse than the obvious correct one on a hot path (list where a set/dict is required; full sort+materialize for top-k; row-by-row join) — even absent a measured regression when the O-class gap is unambiguous.
- A change that regresses the complexity class of an existing hot path (one-pass O(N) -> two-pass or per-row lookups), evidenced by the diff or a plan/benchmark delta.
- A complexity regression already evidenced by a production incident or SLO breach that scales with data volume — blocking regardless of whether a static N-bound proof is complete.
Advisory (do not block): super-linear over a provably bounded/small fixed N; constant-factor inefficiency that does not change the O-class (extra pass, redundant still-O(N log N) sort, `apply` vs. vectorize both O(N)); over-engineering for scale that won't materialize; missing complexity comment / known-quadratic TODO below threshold; suboptimal join strategy the engine auto-corrects (Spark AQE skew/coalesce, optimizer broadcast); repeated work the runtime/JIT likely hoists. A complexity worry with no triggering input, no scale, and no measurement is advisory by rule.

## 5. Anti-patterns to hunt
- Membership test against a list/array inside a loop (`x in list`, `.includes`, `.indexOf`, `.contains`) instead of a pre-built set/dict — the canonical accidental O(N*M).
- Result built by repeated copy: DataFrame `append`/`pd.concat` in a loop, list/string `+=` accumulation, immutable structure rebuilt each iteration — O(N^2) hiding as a loop.
- Row-at-a-time over a vectorizable dataset: pandas `.iterrows()`/`.itertuples()`/`.apply(axis=1)` — flag only when combined with per-row I/O or an external call (DB query, RPC, file open), making the loop N+1 rather than a constant-factor concern; pure columnar-vs-loop without external work is advisory per section 4.
- N+1: DB query / HTTP call / feature-store point-lookup / file open / model load per row; lazy ORM relations walked in a loop with no eager/prefetch.
- Loop-invariant recomputation: `re.compile`, schema/JSON parse, connection open, sort, or full aggregation inside the per-element loop instead of hoisted once.
- Self-join / pairwise comparison without a key, or app-side double loop over two collections, instead of a hash/merge join.
- `collect()`/`toPandas()`/`fetchall()`/whole file or partition read on an unbounded path; multi-pass where one streaming pass with a running aggregate / bounded heap would do.
- Cardinality explosion: CROSS JOIN, join missing its `ON`, non-equi join, or `explode` with no downstream bound, multiplying rows before filtering/aggregation.
- Sort-the-world-to-pick-a-few: full sort + materialize for top-k instead of a bounded heap / `nlargest` / window.
- Worst-case-blind structures: backtracking regex on untrusted input, unbounded recursion/parse depth, hash keyed on attacker-controlled values, sort-merge join on a known-skewed key with no salting/AQE.
- Wrong structure for the operation: list for dedup/membership/grouping where set/dict/Counter is O(1); repeated linear scan for max/min; re-scanning the same source instead of indexing once.
- O(N) goroutine/thread-per-item fan-out: `go func()` per item in a Go range loop or `threading.Thread(target=f, args=(item,))` per row in Python where N is unbounded — exhausts scheduler and RAM; use a fixed worker pool / `concurrent.futures.ThreadPoolExecutor` with bounded `max_workers`.
- JVM string/collection O(N^2) accumulation: Java `String +=` in a loop (no `StringBuilder`) or Scala immutable List `:+` append in a loop — `grep -nE '[+]=.*"|:\+'` on Java/Scala inside a loop block; common in Spark UDFs and per-row handlers.
- Cache-thrash: `@functools.lru_cache`/`@cache` without `maxsize` on a hot path with an unbounded key space (memo table grows O(N)); or `maxsize` set smaller than the live key population, giving a 100% eviction rate and paying both hash-lookup and eviction cost per call.
- Python generator exhaustion: a `map()`/`filter()`/generator expression stored in a variable and iterated twice — silently re-runs the full pipeline on the second pass (or returns empty for an exhausted iterator), hiding an unintended O(2N) double-pass.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/algorithmic-complexity-juror.json`. `ran[]`/`skipped[]` honest. `id` = `algo-<check>-<file>:<line>`. Every blocking finding states N, the current O-class, and the post-fix O-class in `issue`/`suggested_fix`. Nothing outside the JSON.
