---
name: table-format-review
description: The table-format juror's checklist and exact commands — schema evolution, partition-spec evolution, snapshot/time-travel, and ACID commit semantics across Iceberg, Delta Lake, and Hudi.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Table format review

You review ONLY the lakehouse table format surface: schema evolution, partition-spec
evolution, snapshot/time-travel, and ACID/commit semantics. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles/config:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust, `dbt_project.yml` → dbt, a delta log or iceberg metadata → lakehouse.

## 2. Run the checks (mostly reasoning over DDL/metadata/config)
First detect the format: `_delta_log` → Delta Lake; `metadata/*.metadata.json` or
catalog DDL → Iceberg; `.hoodie` → Hudi.

Then reason about the change:
- Schema: is a column **added** (additive, safe in all three) or **dropped/renamed/retyped**?
  Iceberg allows rename and type widening by field-id; Delta needs column-mapping enabled
  for rename/drop; Hudi has its own evolution rules and is strictest on type changes.
- Partition spec: is it being **evolved**? Iceberg supports partition-spec evolution in
  place; Delta and Hudi generally cannot without a rewrite/reload.
- Writes: are they **atomic** — a single commit/transaction — versus a non-transactional
  overwrite that risks a partial/torn snapshot for live readers?

If a CLI is available, gate each on `command -v <tool>` first (e.g. `spark-sql`,
iceberg/delta tooling); if absent, add to `skipped[]` and emit one `info`/non-blocking
finding "`check skipped: <tool> not installed`". Otherwise inspect statically. Never infer
what an un-run check would have found.

## 3. Blocking bar
Set `blocking: true` ONLY for: a schema or partition-spec change incompatible with the
detected format's evolution rules AND with live readers (e.g. a type narrowing, a rename
Delta can't map without column-mapping, a partition-spec change Hudi can't absorb), or a
non-atomic write that risks a partial/torn snapshot. Cite the column/partition field and the
format rule. Everything else is advisory (`warn`/`info`, `blocking: false`). A finding with
no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/table-format-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`. `id` = `tfmt-<check>-<file>:<line>`. Nothing
outside the JSON.
