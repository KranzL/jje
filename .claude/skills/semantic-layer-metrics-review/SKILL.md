---
name: semantic-layer-metrics-review
description: The semantic-layer-metrics juror's checklist and exact commands for additivity, join-fanout, fan/chasm traps, bridge double-count, grain consistency, single-source-of-truth, and metric versioning.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# semantic-layer-metrics review
You review ONLY the correctness and governance of metric math in the semantic/metrics layer (dbt MetricFlow, Cube, LookML, Snowflake/Databricks metric views). PRINCIPAL level — reason about whether the GENERATED SQL double-counts given the declared cardinalities, not whether the YAML merely parses. Hold the bar at what a principal engineer would block, not surface lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the layer from $CHANGED: `semantic_models:`/`metrics:` + `dbt_project.yml` -> MetricFlow; `cube(`/`.yml` under `model/` -> Cube; `*.lkml`/`explore:`/`view:` -> LookML; `CREATE SEMANTIC VIEW`/`metric_view` -> Snowflake/Databricks. Review only those artifacts and apply that engine's fanout/additivity rules.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from `.jje/conventions`), treat its rules as additional blocking bars. From the repo, load where present: the governed metric registry/catalog (certified single-source-of-truth metrics + owner/approver); the dimensional-modeling standard (fact grains, conformed-dimension list); the metric-versioning/change-management policy and deprecation window; the exact-vs-approx policy per metric (financial/regulatory metrics requiring exact); pre-aggregation/rollup definitions and their grains; measure/dimension/entity naming + SCD/time-spine conventions; the bridge/many-to-many list and agreed allocation factors.

## 3. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding; never infer)
- Native parse + semantics: MetricFlow `mf validate-configs` or `dbt parse`/`dbt sl validate`; Cube `cubejs validate` (or `cube validate`); LookML `lookml-validator`/`spectacles`. Parsing clean does NOT clear the math; record skips in skipped[].
- Additivity classification: for every `agg: sum` / LookML `type: sum`, read the column semantics. Tell: `grep -niE 'balance|on_hand|inventory|headcount|mrr|arr|_level|snapshot|eod_|closing_'` summed as plain sum with no `non_additive_dimension:` (MetricFlow) / semi-additive handling.
- Non-additive stored-then-aggregated: grep measures whose `expr`/sql is a ratio/percentage (`/`, `* 100`, `_rate`, `_pct`, `margin`, `ratio`, `avg_`) wrapped in `agg: sum`/`agg: average`. Sum-of-ratios / average-of-averages is wrong; must be a derived/ratio metric over two additive measures (MetricFlow `type: ratio`, Cube two-sum ratio, LookML `type: number` over two sums).
- Fanout protection: per one-to-many join confirm distinct-aggregation guard is on. LookML: grep `symmetric_aggregates: no` (blocking override) and missing/incorrect `relationship:` (defaults to `many_to_one` — silently fans out). MetricFlow/Cube: measure summed at its own grain, join planned by the engine not hand-written. Raw SQL: any `SUM(`/`COUNT(` over a hand-written one-to-many join without `DISTINCT`/dedup is a fanout.
- Chasm-trap: scan a single model/explore/query for TWO fact-grade sources joined through a shared dimension with measures aggregated from BOTH (two `FROM fact_*`/two semantic models, joined on a dimension key, one query). Must be drilled-across — separate passes merged on the conformed dimension. Cite both facts + the shared dimension.
- Fan-trap: a one->many->many chain (order -> order_line -> shipment) with measures on more than one many leg aggregated together — flag for sub-query decomposition.
- Bridge / many-to-many: identify bridge tables (rows = relationship, e.g. account<->customer); a plain SUM crossing one without an allocation/weighting factor counts the measure once per relationship row.
- Entity cardinality audit: MetricFlow `entities:` (`type: primary|unique|foreign`) and LookML join `relationship:` must match the physical key (is the join column actually unique on the 'one' side?). `foreign`/`many_to_one` against a non-unique key makes the planner under-protect fanout.
- Dimension–metric grain consistency: each metric only grouped by dimensions valid at its grain (no order-line measure sliced by a customer-snapshot attribute that fans it out). Confirm `agg_time_dimension`/time-spine is set for cumulative and semi-additive measures.
- Exact-vs-approx: `grep -niE 'count_distinct_approx|approx_count_distinct|use_approximate'`; flag approx on financial/regulatory-exact metrics, and flag exact `count_distinct` materialized in a multi-grain rollup (non-additive — cannot be re-summed across grains).
- Single-source-of-truth: search diff + repo for duplicate/divergent definitions of the same business concept (two metrics aliased `revenue`/`active_users` with different expr/filter), and governed metrics re-derived in raw dashboard/notebook/reverse-ETL SQL instead of consumed from the layer.
- Metric-versioning diff: `git diff "$BASE"...HEAD` over metric/measure defs — flag any change to `expr`, `filter`/`where`, `agg`, grain, or removal/rename on a GOVERNED metric that alters the number, shipped in place without a new version/`deprecate`/migration. Renames of an entity/dimension referenced by a metric are also breaking.
- DAU/WAU/MAU grain duplication: grep multiple measures that are the same `count_distinct` differing only by a hardcoded time window — should be one measure resolved by the query's time grain.

## 4. Blocking bar (everything else advisory; a finding with no evidence is advisory by rule)
Set `blocking: true` only for:
- A semi-additive measure (balance, inventory on-hand, MRR/ARR, headcount, account/EOD snapshot) summed with plain `agg: sum`/`type: sum` and no semi-additive guard (MetricFlow `non_additive_dimension` with `window_choice`, equivalent elsewhere) — sums across time and over-reports. Cite the measure + the time dimension it must not sum over.
- A non-additive quantity (ratio, percentage, margin, rate, average, exact distinct) stored as a column then SUM'd/AVG'd across rows. Must be a derived/ratio metric over two additive components. Cite the expr.
- A one-to-many join inflating a summed/averaged measure with distinct-aggregation protection absent/disabled: LookML `symmetric_aggregates: no` or missing/incorrect join `relationship:`; raw SQL `SUM`/`AVG` over a fanned join without dedup; a MetricFlow/Cube measure hand-joined past its grain. Cite the join + the fanned measure.
- A chasm trap: two fact-grade sources sharing a conformed dimension joined directly with measures from both aggregated in one query (Cartesian double-count). Must be drilled-across. Cite both facts + the shared dimension.
- A measure crossing a many-to-many/bridge relationship with no allocation/weighting factor (counts once per relationship row). Cite the bridge.
- A breaking change to a GOVERNED metric — expr/filter/grain/aggregation change that moves the number, or removal/rename of the metric or a depended-on entity/dimension — shipped in place with no new version, no deprecation window, no consumer migration. Cite before/after.
- Exactness violation: `count_distinct_approx`/approx percentile on a policy-exact (financial/regulatory) metric, OR an exact `count_distinct`/`average`/`percentile` in a multi-grain rollup/pre-aggregation where it is re-summed across grains. Cite the metric + rollup grain.
- Two divergent definitions of the same governed business metric (different expr/filter under one business name), or a governed metric re-implemented in raw dashboard/notebook/reverse-ETL SQL. Cite both definitions.
- Entity cardinality mis-declared (`foreign`/`many_to_one` against a non-unique key) so the planner under-protects fanout for a real measure. Cite the entity/join + the key.

## 5. Anti-patterns to hunt
- Sum-of-ratios / average-of-averages — aggregating a stored ratio/percentage/margin/average instead of dividing two additive measures.
- Summing a balance/inventory/snapshot/MRR level across time as if fully additive (no semi-additive guard).
- SUM/AVG over a one-to-many join with fanout protection off or unavailable (LookML `symmetric_aggregates: no`, missing join relationship, hand-written fanned SQL).
- Joining two fact tables directly and aggregating measures from both (chasm/fan trap) instead of drilling across conformed dimensions.
- Plain SUM through a bridge / many-to-many table with no allocation factor.
- Editing a governed metric's math in place instead of versioning + deprecating; renaming a referenced dimension/entity without treating it as breaking.
- Re-deriving a governed metric in dashboard/notebook/reverse-ETL SQL instead of consuming it; two metrics that compute the 'same' KPI differently.
- Silently swapping exact count_distinct for approx on an exact-required metric, or placing exact distinct/percentile in a multi-grain rollup that re-aggregates it.
- Mis-declaring entity cardinality (foreign/many_to_one against a non-unique key) so the planner under-protects fanout.
- One-metric-per-time-grain duplication (separate DAU/WAU/MAU measures) instead of one measure + grain.
- Slicing a measure by a dimension not valid at its grain (dimension–metric grain mismatch).

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/semantic-layer-metrics-juror.json`. `ran[]`/`skipped[]` honest. `id = sem-<check>-<file>:<line>`. Nothing outside the JSON.
