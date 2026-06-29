---
name: dimensional-modeling-review
description: The dimensional-modeling juror's checklist and exact greps for Kimball grain, additivity, fact-type, surrogate-key, and conformed-dimension defects in star-schema marts.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# dimensional modeling review
You review ONLY the logical dimensional design of new/changed analytics models (dbt/SQL/DDL for star-schema facts and dimensions) against Kimball & Ross, *The Data Warehouse Toolkit* 3rd ed. (2013). PRINCIPAL level — hold the bar at grain/additivity/key/bridge-table correctness a principal would block. Reasoning-led design lane, not physical-layout or data-quality. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
MARTS="$(printf '%s\n' "$CHANGED" | grep -iE 'marts|/(fct|dim|f_|d_)|fact|dim')"
```
Review only mart/presentation models. Do NOT apply dimensional rules to staging/raw/`stg_` files, OBT/wide-table, or Data-Vault raw layer.

## 2. Context to load
Load: modeling standard (Kimball star/DV/Inmon/OBT — calibrate, OBT denormalizes intentionally); layer map and fact-type suffixes (`_snapshot`, `_accum`); conformed-dim/bus-matrix registry (canonical date, customer, product, store); metric/semantic layer (MetricFlow/Cube/LookML/AtScale); per-dim SCD policy; surrogate-key strategy; accepted deviations — do not re-litigate.

## 3. Run the checks
Reasoning over SQL/yaml/DDL for each model in `$MARTS`:
- Grain: `grep -niE 'grain|one row per|granularity' <files>`. No stated grain = advisory; reconstruct from `unique_key`/`GROUP BY`/dbt `unique` test. Verify single, atomic, lowest capture level — not a premature pre-aggregation.
- Grain consistency: every measure and FK must be functionally determined by the grain. Tell: header-level amount (`order_total`) on line-item-grain fact double-counts on SUM; `SUM()`/`MAX()` beside a transaction-grain column.
- Silent grain change: diff `GROUP BY`/`unique_key`/join fan-out before vs after. For any new JOIN, compare source unique-key cardinality to the fact grain key — a 1:N relationship inflates row count; check whether `COUNT(*)` before vs after the join diverges. A grain change without updating the declaration and downstream metric defs is blocking.
- Additivity: classify each measure additive/semi-additive/non-additive. `grep -niE '(/|ratio|rate|pct|percent|avg|average|_per_|margin|cpm|cpc|ctr)' <fact files>` — division materializes a stored non-additive measure. Flag `AVG()` and `COUNT(DISTINCT)`. Semi-additive tell: `grep -niE 'balance|inventory|on_hand|headcount|level|_qty_on|snapshot' <files>` — verify BI/metric layer uses avg/last over time, never SUM over time.
- Fact-type fitness: accumulating snapshot must MERGE/update in place, not insert-only. Transaction fact must be insert-only (no UPDATE of past rows). Periodic snapshot must carry a `snapshot_date` FK and one row per entity per period.
- Null FK: `grep -niE '(_key|_sk)\b.*NULL' <DDL>`. Kimball mandates all fact FK columns NOT NULL pointing to a dedicated unknown-member row (surrogate -1 or 0) in every dimension. A nullable FK silently drops rows on inner joins.
- Bridge table: `grep -niE 'bridge|multi_valued|weighting_factor|allocation_factor' <files>`. A many-to-many fact-to-dimension relationship must use a bridge table; a bridge without an allocation/weighting factor causes double-counting on every SUM aggregate.
- Descriptors-in-fact: `grep -niE '(_name|_desc|_description|_label|_status_text|category_name)\b' <fact files>` — text/labels belong in a dimension; a code with its decode both on the fact is a smell.
- Surrogate key: `grep -niE 'generate_surrogate_key|md5\(|dbt_utils\.surrogate|_sk\b|_key\b' <files>`. Fact FKs must reference dimension surrogate keys; natural/business/composite keys as FKs are a defect on Type-2 dims.
- Conformed dims/facts: `grep -rniE 'dim_(date|customer|product|store)' <repo>` — a second copy or redefined attribute breaks drill-across. `grep -rniE '(revenue|gmv|order_amount|net_sales)' <mart fct_ files>` then diff the defining expressions across any two fct_ models sharing a measure name — same name, different formula breaks every drill-across total.
- Junk vs flag-swarm: `grep -niE '_flag|_ind|is_|has_' <fact files>` — 2+ correlated boolean/low-cardinality columns on the fact where combined cardinality is tractably small should be one junk dimension.
- Role-playing: 2+ FKs to one logical dim must be role-alias views over the conformed dim, not physically copied tables.

## 4. Blocking bar
Set `blocking:true` (cite column + rule violated; a finding with no evidence is advisory):
- Mixed-grain fact: a measure or FK not consistent with declared/reconstructed grain — e.g. header amount on line-item-grain fact, or two event grains unioned into one fact.
- Silent grain change in the diff: fan-out join or changed `GROUP BY`/`unique_key` without updating the grain declaration and downstream metric definitions.
- Non-additive measure stored pre-divided: a ratio/rate/pct/avg materialized as one column instead of additive numerator + denominator — SUM roll-up is arithmetically wrong. Cite the expression.
- Semi-additive measure (balance/inventory/level/headcount) SUMmed across the time dimension by the model or metric layer.
- Many-to-many fact-to-dimension without a bridge table, OR a bridge table with no allocation/weighting factor — both cause silent double-counting on SUM.
- Nullable FK (`*_key`, `*_sk`) on a fact table — silently drops rows on inner joins; Kimball mandates NOT NULL + unknown-member surrogate in every dimension.
- Natural/business/smart key as fact-to-dim FK where the dimension is Type 2.
- Wrong fact type with data-corrupting consequence: transaction fact UPDATEd in place for milestones, or accumulating snapshot insert-only producing milestone duplicates.
- Conformed measure with different formula across two fct_ models sharing the same name — breaks every drill-across total.
- Newly added dim duplicates an existing conformed dim, or redefines a shared conformed attribute so the same name means different things across facts.

Everything else is advisory: missing grain doc when grain is single/atomic; surrogate absent on a small stable Type-1 dim; light snowflaking; junk opportunity with few flags; missing `_snapshot`/`_accum` suffix; undocumented degenerate dimension.

## 5. Anti-patterns to hunt
- No declared grain; grain implicit, reconstructable only from GROUP BY.
- Header-level measure (`order_total`) on a line-item-grain fact — double-counts on SUM.
- Pre-aggregating away the atomic grain in the mart "for performance" — aggregates are additional, not replacements for atomic detail.
- Ratio/pct/rate/avg/unit-price stored as one non-additive column instead of additive numerator + denominator.
- Semi-additive balance/inventory/headcount/level SUMmed across time.
- Many-to-many fact-dim without a bridge table; bridge table with no allocation/weighting factor — both silently double-count SUM aggregates.
- Nullable FK (`*_key`, `*_sk`) on a fact, resolving missing dim members to NULL instead of the unknown-member surrogate.
- Descriptive attributes, decodes, long text, wide labels on the fact; natural/business/smart keys as fact FKs on a Type-2 dim.
- Conformed measure with same name but different formula across fct_ models; duplicate or forked conformed dim (second `dim_date`, `dim_customer`).
- 2+ correlated boolean/low-cardinality flags (tractably small combined cardinality) on the fact instead of one junk dimension.
- Physically copied dim tables for role-playing; degenerate dimension (order/invoice number) needlessly exploded into its own dim table.
- Late-arriving fact referencing a missing dim member via NULL FK instead of a placeholder surrogate (unknown-member row).

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to `iterations/iter-<n>/verdicts/dimensional-modeling-juror.json`. ran[]/skipped[] honest. id = `dim-<check>-<file>:<line>`. Nothing outside the JSON.
