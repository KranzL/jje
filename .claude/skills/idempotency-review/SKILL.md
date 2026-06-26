---
name: idempotency-review
description: The idempotency juror's checklist and exact grep patterns for reasoning over write-path re-run/retry safety.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

# idempotency review
You review ONLY write semantics: whether a re-run or retry duplicates or corrupts data. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks (reasoning lane — rarely an executable oracle)
This lane is mostly reasoning over the write path. There is no scanner that proves idempotency, so reason carefully and state the basis for every finding. Inspect:
- MERGE / upsert keys: do they uniquely identify a row? A non-unique predicate fans out.
- INSERT vs INSERT OVERWRITE vs append: append re-runs duplicate; overwrite must be whole-partition.
- dedup logic: distinct/row_number present and correct on the natural key?
- watermark / high-water-mark: advanced only after commit, inclusive vs exclusive bounds.
- retry / at-least-once delivery: does a redelivered message double-count?
- partitions overwritten atomically (no read-modify-write race, no partial overwrite).

Grep patterns: `MERGE`, `INSERT`, `INSERT OVERWRITE`, `upsert`, `ON CONFLICT`, `dedup`, `distinct`, `watermark`.

If any external tool is used, gate it: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags |
|-------|---------|-------|
| SQL lint of write stmts | `sqlfluff lint $CHANGED` | `--dialect <d>` |

## 3. Blocking bar
Set blocking:true ONLY for: a non-idempotent write (re-run duplicates rows or double-counts), a duplicate-on-retry risk, or a wrong/missing MERGE predicate. Cite the write statement file:line and the key. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/idempotency-juror.json. ran[]/skipped[] honest. id = idem-<check>-<file>:<line>. Nothing outside the JSON.
