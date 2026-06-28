---
name: data-contract-review
description: The data-contract juror's checklist and exact commands for schema evolution and event-contract compatibility.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# data contract review
You review ONLY schema evolution and event-contract compatibility for data pipelines. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks (gate each on the tool being installed)
For every external tool: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags |
| --- | --- | --- |
| Parse models | `dbt parse` | gate on `command -v dbt` |
| Compile contracts | `dbt compile` | flag models whose compiled contract breaks |

## 2b. Mechanical column-type diff (do not skim — a scale cut hides next to a widening)
Build the per-column type delta explicitly; do not eyeball it. For dbt/SQL
schema and contract files, diff every column's declared type and compare the
numbers, because the dangerous changes are SUBTLE: a `decimal(18,4)->decimal(18,2)`
**scale reduction** (silent truncation), a `nullable -> required`/`not_null`
tightening, a widening reverted, a varchar length cut.

```sh
# every changed type/precision/nullability line across schema + model DDL
git diff "$BASE"...HEAD -- '*.yml' '*.yaml' '*.sql' \
  | grep -inE '(decimal|numeric|varchar|char|number)\s*\(|data_type:|not_null|nullable|::(date|timestamp|int|bigint|float)'
```
For EACH column that changed type: extract `(precision, scale)` / length / null-
ability **before vs after** and classify — *widening* (more precision/scale, length
up, required->nullable) is safe; **narrowing** (scale or precision DOWN, length
down, nullable->required, retype to a smaller domain) is breaking on a consumed
column. When `dbt` is available, compare the compiled column types in
`target/manifest.json` before vs after rather than trusting the YAML.

Then find readers and check the version:
- Downstream consumers: `grep -rn '<column_or_model_name>'` across the repo for every reader of a changed column / model ref.
- Event payloads: confirm a version field exists and bumped when the shape changed. Shape changed + version unchanged → breaking.

## 3. Blocking bar
Set blocking:true ONLY for: a backwards-INCOMPATIBLE change (drop/retype/rename a
column, **a precision/scale/length/nullability narrowing**, remove a field, change
an event shape) with live downstream consumers and no version bump or migration.
Cite the column, the before->after type, AND the consumer. A *widening* is not a
narrowing — do not flag it (that look-alike is the trap). Everything else
advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-contract-juror.json. ran[]/skipped[] honest. id = dc-<check>-<file>:<line>. Nothing outside the JSON.
