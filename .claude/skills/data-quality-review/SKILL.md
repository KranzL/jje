---
name: data-quality-review
description: The data quality juror's checklist and exact commands for nulls, duplicates, referential integrity, and constraint coverage.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# data quality review
You review ONLY the data quality surface: nulls, duplicates, referential integrity, and constraint coverage. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks (gate each on the tool being installed)
For every external tool: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags / notes |
|-------|---------|---------------|
| dbt tests on changed models | `dbt test --select <changed_models>` | capture failing test names |
| Great Expectations suite | `great_expectations checkpoint run <suite>` | capture failing expectations |

This lane is mostly reasoning when no runner is installed. Diff the schema yml / test definitions for DROPPED or weakened constraints:
```sh
git diff "$BASE"...HEAD -- '*.yml' '*.yaml' | grep -iE 'not_null|unique|relationships|accepted_values'
```
Grep changed model + schema files for removed tests (lines deleted under a `tests:` or `data_tests:` block). A constraint present at $BASE and absent at HEAD is a removed test.

## 3. Blocking bar
Set blocking:true ONLY for: a failing data test caused by this change, or a dropped/weakened quality constraint (not_null, unique, relationships, accepted_values). Cite the failing test name or the removed constraint as evidence. A missing test runner goes to skipped[] and is NOT a clean pass. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-quality-juror.json. ran[]/skipped[] honest. id = dq-<check>-<file>:<line>. Nothing outside the JSON.
