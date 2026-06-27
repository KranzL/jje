---
name: normalization-relational-review
description: The normalization/relational juror's checklist and exact commands for normal-form design, key design, referential integrity, nullability, dimensional grain, and denormalization tradeoffs.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# normalization / relational design review
You review ONLY the relational/logical DESIGN of new or changed schemas: table shape, keying, referential-integrity design, nullability semantics, dimensional grain, and denormalization tradeoffs. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Stay in lane.
Lane boundary: data-quality owns whether a test EXISTS and passes; data-contract owns whether the schema EVOLVED compatibly; governance owns ownership/PII; you own whether the DESIGN is correct in the first place. Always name the offending table.column, the violating functional dependency or anomaly, and the minimal fix.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the stack from dbt_project.yml, alembic/flyway/liquibase dirs, *.sql, ORM migration folders. Review only changed DDL/migrations/dbt models/schema.yml and warehouse CREATE TABLE.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions/<lane>.md), treat its (blocking) relational rules as additional blocking bars. Read from the repo where present: the team modeling standard and target normal form per layer (operational/OLTP -> 3NF/BCNF; analytical/serving -> star or curated OBT); the surrogate-key convention (integer/identity vs hashed dbt_utils.generate_surrogate_key vs UUID/ULID, whether natural keys must carry a separate UNIQUE); whether the warehouse ENFORCES FK/PK or treats them as informational (Snowflake, BigQuery, Redshift, Databricks/Delta, Iceberg do NOT enforce); the dimensional standard (Kimball/Data Vault/Inmon/OBT) and SCD policy per dimension; the metric/semantic layer grain and join paths; the fact-table grain registry; key-encoding naming conventions (*_id, *_key, *_pk, *_nk); and the list of intentional denormalizations with declared source of truth and refresh path.

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
- Find new/changed tables and keys: `grep -niE 'CREATE TABLE|ALTER TABLE|PRIMARY KEY|UNIQUE|FOREIGN KEY|REFERENCES|NOT NULL|CHECK'` on changed SQL. For each new table confirm a PRIMARY KEY exists and is minimal. No PK is an immediate finding.
- 1NF / repeating-group tell: `grep -niE 'tags|list|csv|_arr|ARRAY<|JSON|JSONB|delimited| comma'` plus column comments. Inspect for delimited multi-value columns or arrays standing in for a junction table, and numbered-column families (phone1, phone2, addr_line_1..n).
- 2NF tell: for any composite PRIMARY KEY (PK over >1 column), inspect every non-key column and ask whether it is determined by only PART of the key (e.g. product_name in (order_id, product_id) PK). Flag the partial dependency by name.
- 3NF/BCNF tell: look for non-key columns that determine other non-key columns (zip -> city/state; dept_id -> dept_name on an employee/fact table; status_code -> status_label). Each transitive dependency should move to its own table/dimension.
- Surrogate vs natural key: when a surrogate PK (id/identity/hash) is added, grep the same table for a UNIQUE on the natural/business key; its ABSENCE means duplicates enter undetected — flag it. Confirm the natural key is still present as an attribute.
- Hashed surrogate inspection: open `generate_surrogate_key()`/`md5()` calls; confirm (a) a column separator (so 12|3 != 1|23), (b) NULL handling/coalesce, (c) the input column set matches the declared grain and is stable. A hash over a mutable or incomplete set is a defect.
- FK target validity: for every `REFERENCES`, confirm the target is the parent PK or a UNIQUE column; an FK pointing at a non-unique column is invalid by design. In unenforced warehouses, confirm a dbt `relationships` test or documented contract backs the join.
- Nullability: grep changed columns for absent `NOT NULL` on domain-mandatory fields (keys, non-optional FKs, audit timestamps, money/quantity on facts). For each nullable FK decide genuine-optional vs sign-the-table-should-split. Note NULLs that silently drop rows in inner joins or skew COUNT/AVG.
- Referential action: `grep -niE 'ON DELETE|ON UPDATE|CASCADE|RESTRICT|SET NULL'`; verify the action matches intent (cascade on child-of-aggregate, restrict on a referenced master, set-null only where the FK is truly nullable).
- Fact-table grain: for changed fact/analytics models, read the model doc/header for the declared grain; reason whether new columns/joins change or mix grains. A join that fans out the fact (1:N treated as 1:1) double-counts additive measures — trace it.
- Many-to-many: confirm a bridge/junction table at the correct grain exists rather than a delimited column or a fact row duplicated per value. Check the bridge has its own composite key or surrogate plus both FKs.
- Denormalization drift: for any duplicated/derived column added downstream, confirm the diff or docs name a source of truth and a refresh/derivation path (dbt dependency, trigger, scheduled rebuild). A copied column with no derivation is a drift hazard.
- Empirical validation (only if a read-only DB connection is reachable — gate each on the connection existing, else skipped[], never inferred): candidate-key/duplicate `SELECT nk_cols, COUNT(*) ... HAVING COUNT(*)>1`; orphan `LEFT JOIN parent WHERE parent.pk IS NULL`; functional-dependency `SELECT determinant, COUNT(DISTINCT dependent) ... HAVING >1`.

## 4. Blocking bar
Set `blocking:true` ONLY when, with named evidence (table.column + dependency/anomaly):
- A new/changed OPERATIONAL table has no PK, or its declared PK is not actually unique for the stated grain (duplicates possible by design).
- A 2NF or 3NF/BCNF violation that produces a real update/insert/delete anomaly on a system-of-record table, with the violating functional dependency named (partial-key dependency, or transitive status_code->label / dept_id->dept_name carried on the base table).
- A surrogate PK introduced WITHOUT a UNIQUE constraint (or a unique test in an unenforced warehouse) on the natural/business key, so duplicate business entities insert undetected.
- An FK (or declared join relationship) whose target is not a PK/UNIQUE column, or a join column with no FK and no relationships test/contract in an unenforced warehouse — referential integrity unprovable, orphans possible.
- A hashed surrogate built without a column separator, without NULL handling, or over an incomplete/mutable input set that does not match the declared grain.
- A 1NF violation where a multi-valued attribute is a delimited string/array in place of a junction/bridge table AND downstream queries filter/group/join on those values.
- An analytics change that mixes grains in one fact table, or introduces a fan-out/fan-trap join that double-counts an additive measure.
- A domain-mandatory column (key, non-optional FK, money/quantity on a fact) left nullable such that NULL silently changes a documented metric-layer measure (excluded from AVG, dropped by inner join).
- A nullable FK introduced where the relationship is actually mandatory, used to dodge normalizing into a child table.
- A denormalized/duplicated column added to the system-of-record (not a clearly downstream serving layer) with no declared source of truth and no refresh/derivation mechanism.
- Any project-local (blocking) relational rule from the conventions overlay is violated.
Everything else is advisory: a BCNF-reachable-but-conflict-free 3NF design, a composite NK that would join cheaper as a surrogate (no demonstrated cost), UUID/wide-string PK cost, missing CHECK/enum domains, a bridge lacking a weighting factor, an undocumented degenerate dimension, intentional OBT downstream of a modeled layer, or surrogate-key exposure in a public URL. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Multi-value in one column: comma/pipe-delimited lists, arrays, or JSON blobs where a junction/bridge table belongs (1NF).
- No PK, or a PK not unique for the real grain; relying on row order or a load timestamp as identity.
- Surrogate PK added but the natural/business key left with no UNIQUE constraint or unique test — the surrogate masks duplicates.
- Natural/mutable business key used as PK and propagated as FKs, so a legitimate business-value change cascades or breaks joins.
- Hashed surrogate with no column separator, no NULL coalescing, or over a mutable/incomplete column set.
- Transitive dependency carried on the base/fact table (zip->city/state, code->label, dept_id->dept_name) instead of normalized into its own table/dimension.
- Partial-key dependency under a composite PK (2NF violation).
- FK pointing at a non-unique column, or a join column with no FK and no relationships test in an unenforced warehouse (referential integrity by hope).
- Nullable FK used to avoid splitting an optional relationship; NULL used as a sentinel for a real state instead of an explicit enum/flag.
- NULL-blind aggregation/joins: a mandatory column left nullable so inner joins drop rows or AVG/COUNT silently change (three-valued-logic trap).
- Grain mixing: facts of different grains in one table, or a 1:N dimension joined as 1:1, fanning out and double-counting additive measures (fan trap / chasm trap).
- OBT/wide table promoted to system of record instead of being a downstream derivative of a modeled layer.
- Premature denormalization for performance with no benchmark and no drift-control.
- SCD-2 history modeled by overwriting (Type 1) where the standard requires Type 2, or Type 2 without effective/expiry/current columns and a fresh surrogate per change.
- ON DELETE CASCADE on a referenced master that silently deletes child history, or RESTRICT where the child should cascade.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to `iterations/iter-<n>/verdicts/normalization-relational-juror.json`. Keep `ran[]`/`skipped[]` honest. `id = norm-<check>-<file>:<line>`. Nothing outside the JSON.
