---
name: interface-review
description: The interface juror's checklist and exact commands for public API / contract stability.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# interface review
You review ONLY the stability of public APIs, exported signatures, and published contracts. Stay in lane: table/schema evolution belongs to table-format or data-contract; storage codec to storage-format; ML splits to data-leakage.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Context to load
Read from the repo where present:
- Versioning policy: SemVer 2.0.0 (semver.org) — MAJOR for incompatible API changes, MINOR for backward-compatible additions, PATCH for fixes.
- API stability labels on changed packages: `stable`/`beta`/`alpha`/`experimental`/`@internal`. Unstable surfaces are advisory-only.
- Published definition — a symbol is published if it appears in: `exports`/`typesVersions` (package.json), `__all__` (Python), `pub` not `pub(crate)` (Rust), an uppercase-exported Go identifier, a registered route, or a `.proto`/OpenAPI/AsyncAPI/Pact contract file checked in.
- Consumer contract files: `.pact` files (Pact consumer-driven contracts, pact.io), `.proto` files with `reserved` blocks or `buf.yaml`, `CHANGELOG.md` for prior deprecation notices.

## 3. Build the surface diff MECHANICALLY (do not skim)
Gate each tool on `command -v`; absent → `skipped[]`:

| Ecosystem | Tool |
|---|---|
| TS/JS | `api-extractor run`; or `tsc -d --emitDeclarationOnly` on `$BASE` and `HEAD`, diff `.d.ts` |
| Go | `apidiff <old-export> <new-export>` (or `gorelease`) |
| OpenAPI/REST | `oasdiff breaking base.yaml head.yaml --fail-on ERR` |
| GraphQL | `graphql-inspector diff old.graphql new.graphql` (github.com/the-guild-org/graphql-inspector) |

If no differ runs, enumerate by hand. Grep tells:
```sh
git diff "$BASE"...HEAD | grep -E '^[-+].*(export (function|const|class|interface|type|enum)|func [A-Z]|pub (fn|struct|enum|trait)|__all__)'
git diff "$BASE"...HEAD -- '*.proto' | grep -E '^[-+]\s*[a-z_].*=\s*[0-9]+'
git diff "$BASE"...HEAD | grep -cE '^-.*@deprecated'  # must be >0 before any hard removal
git diff "$BASE"...HEAD -- package.json '*/version*' VERSION Cargo.toml | grep -iE 'version'
```

For EACH changed published symbol classify additive vs breaking. Breaking even when small:
- Input-position type narrowed (union member removed, optional→required, wider→specific type).
- Output member removed that callers switch on.
- Symbol/route/enum case/CLI flag removed or renamed.
- New REQUIRED field added to a request body or call signature — breaking for all existing callers; MAJOR per SemVer 2.0.0.
- `additionalProperties: false` added to an externally-served JSON Schema (json-schema.org draft-07/2019-09/2020-12) — rejects previously-valid payloads.
- Protobuf field number reused for a different name or type — hard breaking for all encoded wire messages.
- GraphQL field removed, argument made non-null, or type narrowed.

## 4. Blocking bar
Set blocking:true (cite file:line) ONLY for:
- Breaking change (removal/rename/type-narrowing/required-field-addition/field-number-reuse/non-null-widening) on a PUBLISHED, STABLE interface with no accompanying MAJOR version bump.
- `additionalProperties: false` added to an externally-served JSON Schema without a MAJOR bump.
- Deprecated symbol hard-removed with no `@deprecated` in any prior release visible in the diff or changelog.
- Tool-unverifiable: published surface changed, all differs in `skipped[]`, multi-file diff — emit `iface-unverifiable` blocking; grep alone on a large diff is not a clean pass.

Everything else is advisory: new optional response fields; new endpoints or CLI flag additions; deprecation annotations without removal; internal/unexported/`@internal`/`pub(crate)` symbol changes; error-message-only changes; alpha/beta/experimental surface changes; version bump present but magnitude debatable. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Symbol removed from a published surface with no prior `@deprecated` annotation — skip-deprecation-cycle.
- New REQUIRED field added to an existing request body or call signature without a MAJOR bump.
- Protobuf field number reused for a different name/type (`= <N>` reassigned where N was previously used).
- `additionalProperties: false` added to an externally-served JSON Schema — rejects all previously-valid payloads with extra fields.
- GraphQL field removed or argument made non-null without a deprecation cycle or MAJOR bump.
- Type narrowed in an input position disguised as a rename (union member silently dropped, `string | null` → `string`).
- `.pact` contract file modified without a consumer-acknowledged version bump.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/interface-compat-juror.json. ran[]/skipped[] honest. id = iface-<check>-<file>:<line>. Nothing outside the JSON.
