---
name: data-quality-review
description: The data quality juror's checklist and exact commands for nulls, duplicates, referential integrity, and constraint coverage.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# data quality review
You review ONLY the data quality surface: completeness (nulls), uniqueness (duplicates), validity (type/range/pattern constraints), consistency (referential integrity), accuracy (business-rule adherence), and timeliness. PRINCIPAL level. Stay in lane: schema versioning to data-contract; encoding/format to storage-format.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect ecosystem from lockfiles (dbt_project.yml → dbt; pyproject/requirements mentioning pandera/great_expectations → Python; *.soda.yml → Soda Core; plain SQL migration files → DB-level constraints). Review only $CHANGED.

## 2. Context to load
Read before reasoning — distinguishing regression from intentional evolution is impossible without baseline:
- Schema DDL or information_schema for existing DB-level NOT NULL / UNIQUE / FK constraints on changed tables.
- Project baseline null rates or row count ranges (dbt Elementary anomaly config, GE result store, Soda scan history).
- Project conventions (.jje/conventions) for acceptable null thresholds.

## 3. Run the checks (gate each on `command -v`; absent → skipped[] + one info finding; never infer)

| Check | Command | Notes |
|-------|---------|-------|
| dbt core tests | `dbt test --select <changed_models>` | capture failing test names |
| dbt-utils not_null_proportion / recency | grep schema.yml for these test nodes; audit threshold values | flag threshold regression |
| dbt-expectations expect_* nodes | covered by same `dbt test` run | flag removed expect_* nodes |
| Soda Core (SodaCL) | `soda scan -d <datasource> -c configuration.yml checks.yml` | capture check failures |
| Pandera | `pytest` targeting `pa.DataFrameSchema` / `@pa.check_input` / `@pa.check_output` | schema fail = blocking |

Diff constraint definitions regardless of runner:
```sh
git diff "$BASE"...HEAD -- '*.yml' '*.yaml' | grep -iE 'not_null|unique|relationships|accepted_values'
git diff "$BASE"...HEAD -- '*.yml' '*.yaml' | grep -B2 -A5 'not_null\|unique' | grep 'where:'
git diff "$BASE"...HEAD -- '*.sql' | grep -iE 'NOT NULL|UNIQUE|FOREIGN KEY|CHECK\s*\('
```
A test node present at $BASE and absent at HEAD is a dropped constraint. A `where:` clause added or broadened under a not_null/unique node narrows coverage without removing the node — constraint weakening via filter escape.

## 4. Blocking bar
Set blocking:true (cite diff hunk, file:line, or failing test name) ONLY for:
- A not_null / unique / relationships / accepted_values test node **removed** from schema.yml, OR its `where:` clause broadened to exclude previously covered rows — cite the yml diff hunk.
- A DB-level NOT NULL / UNIQUE / FK constraint **dropped** in a migration — cite the ALTER TABLE / DROP CONSTRAINT line.
- A **failing** dbt test, GE expectation, Soda check, or Pandera schema validation caused by this change — cite test/check name.
- A column previously all-non-null now returning nulls with no corresponding not_null test or explicit schema change.
- A row count reduction in a changed model outside the documented expected range, indicating data loss rather than an intended filter change.
Everything else is advisory: new nullable column with no enforcement test; timeliness gap (recency test missing) with no downstream failure; weakened coverage on a non-key column; generous but not-regressed not_null_proportion threshold. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Silent null masking on constrained columns — constraint present but value replaced: `grep -rE 'COALESCE|IFNULL|NVL|ISNULL' $CHANGED`; confirm whether a not_null test covers that column.
- Constraint weakening via where-clause filter escape: `git diff "$BASE"...HEAD -- '*.yml' '*.yaml' | grep -B2 -A5 'not_null\|unique' | grep 'where:'` — narrowed where: keeps test node green while hiding bad rows.
- Fan-out join manufacturing duplicate rows on a stated PK grain: `grep -iE '\bJOIN\b' $CHANGED`; absence of DISTINCT, ROW_NUMBER dedup, or a unique test on the output grain is the tell.
- WHERE IS NOT NULL filter added to a model to hide bad data rather than enforce the constraint — especially when paired with removal of a not_null test.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-quality-juror.json. ran[]/skipped[] honest. id = dq-<check>-<file>:<line>. Nothing outside the JSON.
