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

This lane is mostly reasoning; no scanner judges compatibility for you. Inspect changed schema/model files and event payload definitions by hand:
- Column added → additive, ok. Column dropped, retyped, or renamed → breaking.
- Downstream consumers: `grep -rn '<column_or_model_name>'` across the repo to find every reader of a changed column / model ref.
- Event payloads: confirm a version field exists and that it bumped when the payload shape changed. Shape changed + version unchanged → breaking.

## 3. Blocking bar
Set blocking:true ONLY for: a backwards-INCOMPATIBLE change (drop/retype/rename a column, remove a field, change an event shape) with live downstream consumers and no version bump or migration. Cite the column AND the consumer. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-contract-juror.json. ran[]/skipped[] honest. id = dc-<check>-<file>:<line>. Nothing outside the JSON.
