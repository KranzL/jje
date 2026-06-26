---
name: cost-review
description: The cost juror's checklist and exact commands for scan cost, partitioning, clustering, and file sizing.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# cost review
You review ONLY scan cost, partitioning, clustering, and file sizing. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks (gate each on the tool being installed)
For every external tool: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

This lane is mostly reasoning over the changed SQL/models plus an optional plan from the query engine. Where a warehouse CLI exists, run EXPLAIN / dry-run on changed queries to get a real plan and scanned bytes; the exact command depends on the warehouse, so note it and skip if unavailable.

| Check | Command | Flags a |
| --- | --- | --- |
| BigQuery dry-run | bq query | --dry-run --use_legacy_sql=false |
| Snowflake explain | snowsql | -q "EXPLAIN USING TEXT <sql>" |
| dbt compile | dbt | compile --select <model> |

Static inspection greps when no engine is available:
- `grep -nE 'SELECT[[:space:]]+\*' $CHANGED` — SELECT * on wide tables.
- `grep -niE 'partition_by|cluster_by' $CHANGED` — missing partition/cluster filter on a large table (full scan).
- `grep -niE 'CROSS JOIN|UNNEST|EXPLODE' $CHANGED` — cross joins / exploding arrays (unbounded fan-out).
- `grep -niE 'warehouse[[:space:]]*=|warehouse_size|cluster_size' $CHANGED` — warehouse/cluster size changes.

## 3. Blocking bar
Set blocking:true ONLY for: a full scan on a large table, unbounded fan-out, or a clear runaway warehouse/cluster sizing change. A small-table scan is advisory. Cite the plan line or the query. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/cost-juror.json. ran[]/skipped[] honest. id = cost-<check>-<file>:<line>. Nothing outside the JSON.
