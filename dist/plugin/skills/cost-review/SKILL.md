---
name: cost-review
description: The cost juror's checklist and exact commands for scan cost, warehouse/cluster credit consumption, materialization cost, and result-cache bypass.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# cost review
You review ONLY query scan cost, warehouse/cluster credit consumption, materialization cost (incremental vs full-rebuild), and result-cache bypass. PRINCIPAL level. Physical layout and file format belong to partitioning-layout-review and storage-format-review. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Context to load
Before running checks, read from the repo:
- The project's warehouse tier and documented cost budget or SLA (.jje/conventions, runbooks, README). Without this, "large" and "runaway" cannot be calibrated to baseline.
- The dbt `dbt_project.yml` default materialization and every model-level `materialized:` override touched by the diff.
- Prior cost incidents in .jje/conventions or changelogs.

## 3. Run the checks (gate every external tool on `command -v`; missing -> skipped[] + one info finding; never infer)

Pricing anchors:
- BigQuery on-demand: ~$6.25/TB scanned (1 TB/month free tier). A query scanning >1 TB costs >=~$6.25 per execution.
- Snowflake credits/hour by warehouse size: XS=1, S=2, M=4, L=8, XL=16, 2XL=32, 3XL=64, 4XL=128. A jump of >=2 sizes quadruples or more the hourly credit rate.
- Snowflake and BigQuery both maintain a 24-hour result cache bypassed by non-deterministic functions (`CURRENT_TIMESTAMP`, `RAND`, volatile UDFs) and by DML on the underlying table.

Engine checks:

| Check | Command | Flags |
| --- | --- | --- |
| BigQuery dry-run | `bq query` | `--dry_run --use_legacy_sql=false` |
| Snowflake explain | `snowsql` | `-q "EXPLAIN USING TEXT <sql>"` |
| dbt compile | `dbt` | `compile --select <model>` |

For BigQuery dry-run: flag `processedBytes > 1_000_000_000_000` (>1 TB).

Static greps when no engine is available:
- `grep -nE 'SELECT[[:space:]]+\*' $CHANGED` — SELECT * on wide tables.
- `grep -niE 'CROSS[[:space:]]+JOIN' $CHANGED` — potential unbounded fan-out.
- `grep -niE 'UNNEST|LATERAL[[:space:]]+FLATTEN|EXPLODE' $CHANGED` — array explosion with no cardinality guard.
- `grep -niE 'CURRENT_TIMESTAMP|CURRENT_DATE|RAND\(\)' $CHANGED` — result-cache bypass.
- `grep -niE 'warehouse[[:space:]]*=|warehouse_size|cluster_size' $CHANGED` — warehouse/cluster size changes.
- `grep -niE "materialized[[:space:]]*:[[:space:]]*['\"]?table" $CHANGED` — model changed to full-rebuild.

## 4. Blocking bar
Set blocking:true (cite file:line and the pricing anchor or plan evidence) ONLY for:
- A BigQuery query whose dry-run `processedBytes` exceeds 1 TB (>=~$6.25 per run at on-demand pricing) — cite the reported bytes.
- A warehouse size change of >=2 sizes without `auto_suspend` — at least quadruples the credit rate per Snowflake's documented credit model with no automatic shutoff.
- A dbt model changed from `materialized: incremental` to `materialized: table` without documented justification — forces a full-table rebuild on every dbt run indefinitely.
Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `materialized: incremental` changed to `materialized: table` on a large model — full rebuild every run; grep `materialized.*table` in changed `.sql`/`.yml` files.
- `CURRENT_TIMESTAMP()`, `CURRENT_DATE`, `RAND()`, or a volatile UDF in `SELECT` — defeats Snowflake and BigQuery 24-hour result caches on every re-execution.
- A CTE referenced more than once in a single Snowflake query — re-evaluated on each reference unlike a temp table; use a temp table for repeated CTEs.
- `CROSS JOIN` with no row-limiting `WHERE` clause or documented cardinality guard — unbounded fan-out.
- `UNNEST` / `LATERAL FLATTEN` on an array column with no cardinality estimate or `LIMIT`.
- Warehouse size jump of >=2 sizes (e.g. S->L is 4x credits/hour per Snowflake's documented credit model) with `auto_suspend` absent or disabled.
- `SELECT *` on a wide columnar table — reads all columns, defeating columnar projection pruning.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/cost-juror.json. ran[]/skipped[] honest. id = cost-<check>-<file>:<line>. Nothing outside the JSON.
