---
name: interface-review
description: The interface juror's checklist and exact commands for public API / contract stability.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# interface review
You review ONLY the stability of public APIs, exported signatures, and published contracts. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks
This lane is mostly reasoning over the diff of the public/exported surface against the base ref. Inspect for: changed exported function/method signatures, removed or renamed public symbols, changed REST/GraphQL routes, changed protobuf/OpenAPI/JSON-schema files, changed CLI flags. Then check for a matching version bump (package version, API version) whenever a published surface changed.

Language tells to grep on the changed files:
- Go: `git diff "$BASE"...HEAD -- '*.go' | grep -E '^[-+]func [A-Z]'` (capitalized exports)
- Python: `grep -nE '__all__|^def [a-z]|^class [A-Z]' $CHANGED` (public names)
- Rust: `git diff "$BASE"...HEAD | grep -E '^[-+]\s*pub (fn|struct|enum|trait)'`
- TS/JS: `git diff "$BASE"...HEAD | grep -E '^[-+].*export (function|const|class|interface|type)'`
- Contracts: `git diff --name-only "$BASE"...HEAD | grep -E '\.proto$|openapi|swagger|\.json-schema|schema\.graphql'`
- Version bump: `git diff "$BASE"...HEAD -- package.json '*/version*' VERSION | grep -iE 'version'`

External tools (gate each on `command -v <tool>` first; if absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed"; never infer what an un-run check would have found):

| Check | Command | Flags a |
|-------|---------|---------|
| Protobuf compat | `buf breaking --against "$BASE"` | `--error-format=json` |
| OpenAPI diff | `oasdiff breaking base.yaml head.yaml` | `--fail-on ERR` |
| Go API surface | `apidiff old new` | (none) |

## 3. Blocking bar
Set blocking:true ONLY for: a BREAKING change to a PUBLISHED interface (removed/renamed/retyped public symbol, removed route, incompatible request/response) with no accompanying version bump. Additive changes (new optional field, new endpoint) are fine. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/interface-compat-juror.json. ran[]/skipped[] honest. id = iface-<check>-<file>:<line>. Nothing outside the JSON.
