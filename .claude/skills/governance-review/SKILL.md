---
name: governance-review
description: The governance juror's checklist and exact commands for ownership, PII handling, and catalog/lineage registration.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# governance review
You review ONLY ownership, PII handling, and catalog/lineage registration. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks
This lane is mostly reasoning over yml/config. No external scanner is required; inspect by hand. If you do reach for a tool, gate it: `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

| Check | Command | Flags |
| --- | --- | --- |
| Locate schema/meta | `git diff "$BASE"...HEAD -- '*.yml' '*.yaml' '*.sql'` | name-only first, then full |
| PII column scan | `grep -niE 'email|ssn|social|phone|address|name|first|last|dob|birth|\bip\b|lat|long|credit_card' $CHANGED` | -niE |
| Tag/mask/owner | `grep -niE 'tags:|meta:|owner:|pii|mask' $CHANGED` | -niE |

For every new/changed column matching the PII name list, confirm it is tagged/masked/classified in model meta. For governed-tier models, confirm a named owner exists (meta: owner or a CODEOWNERS entry). Confirm catalog/lineage registration via meta blocks and tags.

## 3. Blocking bar
Set blocking:true ONLY for: untagged/unmasked PII, or a governed-tier change with no named owner. Cite the column and the missing tag/owner. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/governance-juror.json. ran[]/skipped[] honest. id = gov-<check>-<file>:<line>. Nothing outside the JSON.
