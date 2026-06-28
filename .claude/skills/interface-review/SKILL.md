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

## 2. Build the surface diff MECHANICALLY (do not skim)
A breaking change is easy to miss by reading — especially a **type narrowing**
buried among additive edits. So enumerate the public surface delta, symbol by
symbol, tool-backed where possible. Prefer a real API-differ over grep:

External tools — gate each on `command -v <tool>`; if absent, add to `skipped[]`
(and see the hard rule in step 3 about an *unverifiable* surface):

| Ecosystem | Tool-backed surface diff |
|---|---|
| TS/JS | `tsc -d --emitDeclarationOnly` on `$BASE` and `HEAD`, then `diff` the emitted `.d.ts`; or `api-extractor run` and diff the API report; or `attw`/`api-extractor` |
| Go | `apidiff <old-export> <new-export>` (or `gorelease`) |
| Protobuf | `buf breaking --against "$BASE"` |
| OpenAPI/REST | `oasdiff breaking base.yaml head.yaml --fail-on ERR` |
| Python | `griffe check <pkg> -a "$BASE"` (or `pyright` on the stub) |

If no differ is available, do the diff by hand but EXHAUSTIVELY: list every
exported symbol that changed and classify each. Tells:
`git diff "$BASE"...HEAD | grep -E '^[-+].*(export (function|const|class|interface|type|enum)|^[-+]func [A-Z]|pub (fn|struct|enum|trait)|__all__)'`

For EACH changed exported symbol decide **additive vs breaking**, and treat these
as breaking even when they look small:
- a parameter/field/alias type **narrowed** (a union member removed, `string|number`->`string`, optional made required, a wider type made specific) — breaking in any **input** position;
- a return/output type widened with a removed member that callers switch on;
- a removed/renamed symbol, route, enum case, or CLI flag; a retyped field.
Then check for a matching version bump:
`git diff "$BASE"...HEAD -- package.json '*/version*' VERSION Cargo.toml | grep -iE 'version'`.

## 3. Blocking bar
Set blocking:true for: a BREAKING change to a PUBLISHED interface (removed/renamed/
retyped/**narrowed** public symbol, removed route, incompatible request/response)
with no accompanying major version bump. Additive changes (new optional field, new
endpoint) are fine.

**Tool-unverifiable rule:** if the change touches a published surface (exports,
routes, contract files) AND no API-differ could run (all in `skipped[]`), you
cannot certify compatibility by eye on a large diff — emit one `blocking: true`
finding `iface-unverifiable: published surface changed, no API-differ available
(install tsc/api-extractor/apidiff/buf/oasdiff)`. A surface change reviewed by
grep alone on a multi-file diff is not a clean pass. A finding with no evidence is
advisory by rule; this rule IS the evidence (the absent tool).

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/interface-compat-juror.json. ran[]/skipped[] honest. id = iface-<check>-<file>:<line>. Nothing outside the JSON.
