---
name: structure-review
description: The structure juror's checklist and exact commands for naming, module boundaries, and agreed conventions.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# structure review
You review ONLY structure: naming, module boundaries, and the repo's agreed conventions/standards. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks (gate each on the tool being installed)
For every external tool: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags a |
| --- | --- | --- |
| Python lint | `ruff check $CHANGED` | `--no-fix` |
| Go lint | `golangci-lint run` (else `go vet ./...`) | — |
| Rust lint | `cargo clippy` | `--no-deps` |
| JS/TS lint | `eslint $CHANGED` | `--no-fix` |

This lane is mostly reasoning. Read any conventions file present (CONTRIBUTING, .editorconfig, STYLE/conventions doc, CLAUDE.md) to learn the agreed standard, then inspect $CHANGED against it:
- naming: `grep -nE '\b(temp|data|foo|util2|helper2)\b' $CHANGED` and flag identifiers that fight the prevailing case/style.
- boundaries: trace new imports/exports; flag layering violations (e.g. core importing UI, cross-module reach-through).
- conventions: compare file placement, module size, and public surface to the documented standard.

## 3. Blocking bar
Set blocking:true ONLY for: a violation that breaks the build or violates an agreed, documented standard. Pure taste/preference is advisory, never blocking. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/structure-juror.json. ran[]/skipped[] honest. id = struct-<check>-<file>:<line>. Nothing outside the JSON.
