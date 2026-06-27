---
name: partitioning-layout-review
description: The partitioning-layout juror's checklist and exact commands for partition design, small-files, file/row-group sizing, compaction, and clustering.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# partitioning layout review
You review ONLY the datalake physical layout: partition design, the small-files problem, file/row-group sizing, compaction, and clustering/Z-order. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles/config (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml, delta log, iceberg metadata).

## 2. Run the checks (gate each on the tool being installed)
For every external tool: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

This lane is reasoning over table DDL and write/job config. Check:
- Partition column cardinality: partitioning by a high-cardinality column (user_id, a raw timestamp) explodes into tiny files; a date/hour grain or a bucketed key is usually right.
- Whether partition columns match common query predicates — else there is no pruning benefit.
- Whether an append/streaming table has a compaction/OPTIMIZE strategy.
- Target file size: aim ~128MB-1GB; many <16MB files is the small-files problem.

Static inspection greps:
- `grep -niE 'PARTITIONED BY|partitionBy' $CHANGED` — partition keys; judge cardinality and predicate match.
- `grep -niE 'bucketBy|clusterBy|ZORDER' $CHANGED` — clustering / Z-order layout.
- `grep -niE 'OPTIMIZE|compact|vacuum' $CHANGED` — compaction strategy on append/streaming tables.
- `grep -niE 'coalesce|repartition|maxRecordsPerFile|target-file-size' $CHANGED` — output file sizing.

## 3. Blocking bar
Set blocking:true ONLY for: a high-cardinality partition column (small-files explosion), a missing compaction strategy on an append/streaming table, or a partition scheme that does not match the query predicates (no pruning). Cite the partition column and the cardinality/predicate mismatch. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/partitioning-layout-juror.json. ran[]/skipped[] honest. id = part-<check>-<file>:<line>. Nothing outside the JSON.
