---
name: dimensional-modeling-review
description: The dimensional-modeling juror's checklist and exact greps for Kimball grain, additivity, fact-type, surrogate-key, SCD2, and conformed-dimension defects in star-schema marts.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# dimensional modeling review
You review ONLY the LOGICAL dimensional design of new/changed analytics models (dbt/SQL/DDL for star-schema fact & dimension tables, plus the metric/semantic layer on them) against Kimball's four steps: declare process, declare grain, choose dimensions, choose facts. PRINCIPAL level — hold the bar at grain/additivity/key/SCD correctness a principal would block, not surface lint. This is a reasoning-led design lane, not physical-layout or data-quality. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
MARTS="$(printf '%s\n' "$CHANGED" | grep -iE 'marts|/(fct|dim|f_|d_)|fact|dim')"
```
Review only mart/presentation models. Do NOT apply dimensional rules to staging/raw/`stg_` files, OBT/wide-table, or Data-Vault raw layer.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its rules as additional blocking bars. From the spec's context_needed, read where present: the modeling standard (Kimball star vs Data Vault vs Inmon vs OBT — calibrate, OBT denormalizes intentionally); the layer map (`stg_`/`int_`/`fct_`/`dim_`, staging/ vs marts/); fact-type suffixes (`_snapshot`, `_accum`); the conformed-dimension registry / bus matrix (canonical date, customer, product, store and their grain); the metric/semantic layer (MetricFlow/Metrics, Cube, LookML, AtScale); per-dimension SCD policy and history mechanism (dbt snapshots, MERGE, CDC); surrogate-key strategy and whether durable keys are retained; date-dimension convention and smart-integer key format; and documented intentional deviations (accepted pre-aggregation, stored ratios, deliberate snowflaking) — do not re-litigate those.

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
Mostly reasoning over the SQL/yaml/DDL. For each fact/dim model in $MARTS:
- Grain declaration: `grep -niE 'grain|one row per|granularity' <files>` in header/yaml/docs. No stated grain on a fact = advisory; reconstruct grain from `unique_key`, `GROUP BY`, or the dbt `unique` test columns and verify it is single and atomic (lowest capture level, not a premature pre-aggregation).
- Grain consistency (core): every measure in the SELECT and every dimension FK must be functionally determined by the declared/reconstructed grain. Tell: a header-level amount (`order_total`) on a line-item-grain fact (double-counts on SUM), or a SUM()/MAX() measure beside a transaction-grain column.
- Silent grain change: `git diff` the GROUP BY / `unique_key` / join fan-out before vs after. A new fan-out JOIN or added/removed GROUP BY column changes grain silently.
- Additivity audit: classify each measure additive / semi-additive / non-additive. `grep -niE '(/|ratio|rate|pct|percent|avg|average|_per_|margin|cpm|cpc|ctr)' <fact files>` then confirm a division materializes a stored measure (`x / y AS z`). Also flag stored `AVG()` and `COUNT(DISTINCT)` as non-additive.
- Semi-additive tell: `grep -niE 'balance|inventory|on_hand|headcount|level|_qty_on|snapshot' <files>` — balances/levels in a periodic snapshot; verify metric/BI layer uses avg/last over time, never SUM over time.
- Fact-type fitness: infer type from name/yaml. Accumulating-snapshot (`_accum`, multiple `*_date` FKs, lag/duration measures) must update rows in place — check load uses MERGE/incremental update, not insert-only. Transaction facts must be insert-only (no UPDATE of past rows). Periodic snapshot must carry a `snapshot_date` FK and one row per entity per period.
- Descriptors-in-fact (Rule 7): `grep -niE '(_name|_desc|_description|_label|_status_text|address|category_name)\b' <fact files>` — text/labels that belong in a dimension; a code with its decode both on the fact is a smell.
- Surrogate-key leakage: `grep -niE 'generate_surrogate_key|md5\(|dbt_utils\.surrogate|_sk\b|_key\b' <files>`. Fact FKs must reference dimension surrogate keys, not raw natural/business/smart keys (joining on `customer_email`, `product_sku`).
- Point-in-time SCD2: if a referenced dim is Type 2, the fact load must resolve the AS-OF key (join on natural key AND `event_date BETWEEN effective/expiry`), NOT `WHERE is_current = true` — the latter retro-stamps current attributes onto historical facts.
- SCD2 completeness: a Type-2 dim must have effective/expiry/current_flag (or dbt `dbt_valid_from/to`) AND a durable/natural key. Without the durable key, versions can't be joined.
- Conformed duplication: `grep -rniE 'dim_(date|customer|product|store)' <repo>` — a newly added second date/customer dim, or a redefined shared attribute, breaks drill-across.
- Junk vs flag-swarm: `grep -niE '_flag|_ind|is_|has_' <fact files>` — a swarm of low-cardinality flags on the fact (or one tiny dim each) should be one junk dimension.
- Role-playing: multiple FKs to one logical dim (two+ `*_date_key`, origin/dest) must be role aliases (views over one conformed dim), not physically copied dim tables.
- Snowflake detection: a dim joining out to normalized sub-tables (`dim_x` -> `dim_x_category`, `lookup_*`) — flag as denormalization tradeoff unless a large shared low-cardinality outrigger.
- Factless recognition: an event/coverage table with only FKs and no measure — verify it's intentionally factless (or carries a degenerate count), not a mistake; flag `1 AS count` only if it obscures real measures.
- Metric/semantic layer: open touched dbt metric/MetricFlow/Cube/LookML defs — each measure must declare the correct aggregation (`agg: sum/average/count_distinct`) consistent with its additivity and be defined on a model at the right grain.

## 4. Blocking bar
Set blocking:true ONLY for (cite column + the grain/key/rule it violates; a finding with no evidence is advisory):
- Mixed-grain fact: a measure or dimension FK not consistent with the declared/reconstructed grain (Kimball Rule 4) — e.g. header-level amount on a line-item-grain fact, or two event grains unioned into one fact.
- Silent grain change in the diff: a fan-out join or changed GROUP BY/`unique_key` alters grain without the grain declaration and downstream metric defs being updated.
- Non-additive measure stored pre-divided: a ratio/rate/percentage/average materialized as a single fact column instead of additive numerator + denominator, so roll-up SUM is arithmetically wrong. Cite the divided expression.
- Semi-additive measure (balance/inventory/level/headcount) SUMmed across the time dimension by the model or metric layer. Cite the measure and the time roll-up.
- Point-in-time-incorrect SCD2: a fact load joins a Type-2 dim on `is_current = true` (or the natural key without the effective/expiry as-of window), retro-stamping historical rows. Cite the join.
- Natural/business/smart key used as fact-to-dimension join key (or fact grain) where the dimension is Type 2. (Surrogate omission on a static Type-1-only dim is advisory.)
- Wrong fact type with data-corrupting consequence: a transaction fact whose rows get UPDATEd in place for milestones (should be accumulating snapshot), or an accumulating/append load that inserts duplicate milestone rows instead of updating.
- A newly added dimension duplicates an existing conformed/enterprise dimension, or redefines a shared conformed attribute/metric so a name means different things across facts. Cite the existing conformed dim.

Everything else is advisory: missing grain doc when grain is single/atomic; surrogate absent on a small stable Type-1 dim; light-snowflake judgment calls; junk-dimension opportunity with few flags; naming without `_snapshot`/`_accum`; undocumented degenerate dimension; metric measure lacking an additivity annotation though the column is additive; date dim using raw timestamp instead of the smart-integer (YYYYMMDD) key.

## 5. Anti-patterns to hunt
- No declared grain; grain implicit, reconstructable only from GROUP BY.
- Mixing transaction and summary/header measures at different grains in one fact (Rule 4).
- Pre-aggregating away the atomic grain in the mart "for performance" so unpredictable queries can't be answered (Rule 1 — load atomic detail; aggregates are additional, not replacements).
- Storing a derived ratio/percentage/rate/average/unit-price as one non-additive fact column instead of numerator + denominator.
- SUMming a semi-additive balance/inventory/headcount across time.
- Descriptive attributes, decodes, long text, or wide labels on the fact instead of a dimension (Rule 7).
- Cryptic operational codes on the fact with no conformed dimension to decode them.
- Natural/business/smart keys (sku, email, composite intelligent keys) as fact FKs instead of dimension surrogates (Rule 8).
- Type-2 join using `is_current = true` at fact-load time, retro-assigning current attributes to historical events.
- Type-2 dim missing effective/expiry/current-flag or a durable/natural key, making history un-joinable.
- Re-creating an existing conformed dimension (second `dim_date`, `dim_customer`), or forking a shared attribute's definition.
- A swarm of correlated low-cardinality flags on the fact (or one tiny dim per flag) instead of one junk dimension.
- Physically copying a dimension to play multiple roles (`order_date_dim`, `ship_date_dim`) instead of role-playing aliases/views over one conformed date dim.
- Gratuitous snowflaking — normalizing a dim into lookup sub-tables for small low-cardinality attributes, adding join cost with no benefit.
- Inventing a fake/constant measure to avoid modeling a legitimately factless (coverage/event) table.
- A fact with no foreign key to a date dimension (Rule 3).
- A degenerate dimension (order/invoice number) needlessly exploded into its own one-row-per-value dimension table.
- Metric-layer measure with an aggregation type (sum) inconsistent with the measure's additivity, or defined on a model at the wrong grain.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to `iterations/iter-<n>/verdicts/dimensional-modeling-juror.json`. ran[]/skipped[] honest. id = `dim-<check>-<file>:<line>`. Nothing outside the JSON.
