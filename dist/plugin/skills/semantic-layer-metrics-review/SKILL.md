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
Detect the layer from $CHANGED: `semantic_models:`/`metrics:` + `dbt_project.yml` -> MetricFlow; `cube(`/`.yml` under `model/` -> Cube; `*.lkml`/`explore:`/`view:` -> LookML. Review only those artifacts and apply that engine's fanout/additivity rules.

## 2. Reference canon (anchor every blocking call to one of these)
- **Kimball, *The Data Warehouse Toolkit* 3rd ed. 2013**: chasm trap = two fact-grade sources at different grains sharing a conformed dimension key with measures from both fanned into one query → Cartesian double-count; fan trap = one→many→many chain with measures on more than one many leg aggregated together; drilling-across = separate aggregation passes merged on the conformed dimension — the only correct path for chasm-trapped facts.
- **dbt MetricFlow OSS spec** — `type: simple | ratio | derived | cumulative | conversion`. `type: cumulative` takes at most one of `window:` or `grain_to_date:` (mutually exclusive; omitting both yields an all-time accumulation — verify intentional). `type: conversion` requires `base_measure:`, `conversion_measure:`, and a shared `entity:`; `window:` is optional (omission defaults to all-time accumulation); conversion event timestamp must post-date the base event.
- **LookML fanout-safe aggregates**: `type: sum` + `sql_distinct_key` (explicit safe path) or `symmetric_aggregates: yes` (engine-level). Failure: `type: sum` in an explore with `relationship: many_to_one|many_to_many` and no `sql_distinct_key` — fanout fires silently. `symmetric_aggregates: no` disables the engine guard entirely.
- **Cube.js semi-additive guard**: For period-end snapshot measures (balance, inventory, snapshot), use measure `type: 'max'`/`'min'`. A specific `trailing:`/`leading:` window computes rolling cumulative aggregates. Absent guard on a balance/snapshot measure = plain sum across time.

## 3. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from `.jje/conventions`), treat its rules as additional blocking bars. From the repo, load where present: the governed metric registry/catalog; the dimensional-modeling standard (fact grains, conformed-dimension list); the exact-vs-approx policy per metric (financial/regulatory metrics requiring exact); pre-aggregation/rollup definitions and their grains; bridge/many-to-many list and agreed allocation factors.

## 4. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding; never infer)
- **Native parse**: `mf validate-configs`/`dbt parse`; LookML `spectacles`. Parse-clean does NOT clear the math; record skips.
- **Additivity**: `grep -niE 'balance|on_hand|inventory|headcount|mrr|arr|_level|snapshot|eod_|closing_'` summed as plain `agg: sum`/`type: sum` with no semi-additive guard — MetricFlow `non_additive_dimension:` + `window_choice:`; Cube `type: max`/`type: min` for snapshots; LookML appropriate semi-additive `type:`.
- **Non-additive stored-then-aggregated**: grep measures whose `expr`/sql contains `/`, `* 100`, `_rate`, `_pct`, `margin`, `ratio`, `avg_` wrapped in `agg: sum`/`agg: average`. Must be `type: ratio` (MetricFlow), a two-sum ratio (Cube), or `type: number` over two sums (LookML).
- **Non-composable aggregates in rollups**: `grep -niE 'PERCENTILE_CONT|MEDIAN\b|MODE\('` used as measure `expr` values materialized in pre-aggregations/rollups. Like exact `count_distinct`, these cannot be re-summed across grains — silently wrong.
- **LookML fanout**: `grep -niE 'type:\s+sum\b' *.lkml` — for each hit confirm the enclosing explore has `sql_distinct_key:` on that measure or `symmetric_aggregates: yes`; flag `relationship: many_to_one|many_to_many` without `sql_distinct_key`. Flag `symmetric_aggregates: no` (blocking).
- **MetricFlow cumulative config**: `grep -n 'type:\s*cumulative'` — verify at most one of `window:` or `grain_to_date:` is present; flag omission of both as advisory if not confirmed intentional all-time accumulation.
- **MetricFlow conversion config**: `grep -n 'type:\s*conversion'` — verify `base_measure:`, `conversion_measure:`, and a shared entity all present; `window:` is optional; flag missing entity or entity mismatch.
- **NULL propagation**: for `type: ratio`/`type: number` over two measures, confirm denominator has a `NULLIF`/`COALESCE` guard. Flag `fill_nulls_with: 0` on a governed metric (alters the number; is a policy change).
- **Chasm trap**: scan for a single model/explore/query joining two fact-grade sources through a shared dimension key with measures from both aggregated together. Must be drilled-across. Cite both facts + the shared dimension.
- **Fan trap**: one→many→many chain with measures on more than one many leg aggregated together. Flag for sub-query decomposition.
- **Bridge / many-to-many**: plain SUM crossing a bridge table without an allocation/weighting factor counts once per relationship row.
- **Entity cardinality**: MetricFlow `entities:` and LookML `relationship:` must match the physical key (is the 'one' side actually unique?). `foreign`/`many_to_one` against a non-unique key causes the planner to under-protect fanout.
- **Grain consistency**: each metric grouped only by dimensions valid at its grain; `agg_time_dimension`/time-spine set for cumulative and semi-additive measures.
- **Exact-vs-approx**: `grep -niE 'approx_count_distinct'`; flag approx on policy-exact metrics; flag exact `count_distinct`/`PERCENTILE_CONT`/`MEDIAN` in a multi-grain rollup (non-composable — cannot be re-summed).
- **Single-source-of-truth**: search diff + repo for duplicate/divergent definitions of the same business concept (two metrics aliased `revenue`/`active_users` with different `expr`/filter).
- **Metric-versioning diff**: `git diff "$BASE"...HEAD` over metric/measure defs — flag any change to `expr`, `filter`/`where`, `agg`, grain, or removal/rename on a GOVERNED metric that moves the number, shipped in place.
- **DAU/WAU/MAU grain duplication**: `grep -niE 'count_distinct.*(DATEADD|INTERVAL|BETWEEN)'` — multiple measures with the same `count_distinct` expression differing only by a hardcoded date offset should be one measure resolved by the query's time grain.

## 5. Blocking bar
Set `blocking: true` (cite file:line and the evidence) ONLY for:
- Semi-additive measure (balance, inventory, MRR/ARR, headcount, EOD snapshot) with plain `agg: sum`/`type: sum` and no guard — MetricFlow `non_additive_dimension:`, Cube `type: max`/`type: min` for snapshots, LookML semi-additive type. Sums across time and over-reports.
- Non-additive quantity (ratio, percentage, margin, rate, stored average, `PERCENTILE_CONT`/`MEDIAN`/`MODE`, exact distinct) SUM'd/AVG'd across rows; must be a derived/ratio metric over two additive components.
- LookML `type: sum` in a many-to-one or many-to-many explore without `sql_distinct_key` and without `symmetric_aggregates: yes`; or `symmetric_aggregates: no` explicitly disabling the guard.
- MetricFlow `type: conversion` missing `base_measure:`, `conversion_measure:`, or shared `entity:`.
- Chasm trap: two fact-grade sources at different grains joined directly with measures from both aggregated in one query. Must be drilled-across.
- Bridge/many-to-many crossed with a plain SUM and no allocation factor.
- Entity cardinality mis-declared (`foreign`/`many_to_one` against a non-unique key) causing the planner to under-protect fanout for a real measure.
- Breaking change on a GOVERNED metric (expr/filter/grain/agg altered, or metric/entity/dimension removed/renamed) shipped in place.
- Exactness violation: approx aggregate on a policy-exact metric; or exact `count_distinct`/`PERCENTILE_CONT`/`MEDIAN` in a multi-grain rollup/pre-aggregation where it is re-summed across grains.
- Two divergent definitions of the same governed business metric under one business name.

Everything else is advisory: new unregistered metrics that do not conflict with any governed definition; `fill_nulls_with: 0` on a governed metric (policy question, not a math error); non-composable exact aggregates outside rollup contexts; stylistic naming issues; DAU/WAU/MAU duplication where no governed definition exists; fan/chasm pattern in an unused draft model; MetricFlow `type: cumulative` with neither `window:` nor `grain_to_date:` (all-time accumulation — advisory unless confirmed unintentional). A finding with no evidence is advisory by rule.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/semantic-layer-metrics-juror.json`. `ran[]`/`skipped[]` honest. `id = sem-<check>-<file>:<line>`. Nothing outside the JSON.
