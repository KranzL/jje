---
name: data-contract-review
description: The data-contract juror's checklist and exact commands for schema evolution and event-contract compatibility.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# data contract review
You review ONLY schema evolution and event-contract compatibility across SQL/dbt, Avro, Protobuf, AsyncAPI, and CloudEvents surfaces. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Reference spec numbers
- **Avro spec**: BACKWARD = new readers decode old records (requires `"default"` on every added field). FORWARD = old readers decode new records. FULL = both. Removing a field is FORWARD-INCOMPATIBLE (old readers can't decode new records missing it); removing an enum symbol is BACKWARD-INCOMPATIBLE (new readers hit an unknown symbol in old data).
- **Confluent Schema Registry**: canonical gate is `POST <registry>/compatibility/subjects/<subject>/versions/latest`; `"is_compatible":true` = pass. Gate on `SCHEMA_REGISTRY_URL`.
- **Protobuf Language Guide**: deleting or reusing a field number with a different wire type silently corrupts deserialization; `reserved` is the required mitigation.
- **dbt 1.5+ contracts**: `contract: enforced: true` + column-level `data_type`. `dbt parse`/`dbt compile` catch shape violations; `dbt test` catches `not_null`/`unique`/`accepted_values` violations at data time.
- **AsyncAPI v2/v3**: authoritative spec for event-channel contracts. **CloudEvents v1.0 (CNCF)**: `id`, `specversion`, `type`, `source` are required envelope fields; removing or narrowing any is breaking.

## 3. Run the checks (gate every external tool on `command -v`; absent → skipped[] + one info finding; never infer)
**SQL / dbt** — diff column type/nullability; flag narrowings (precision/scale down, length down, nullable→required, retype to smaller domain); widening is safe:
```sh
git diff "$BASE"...HEAD -- '*.yml' '*.yaml' '*.sql' \
  | grep -inE '(decimal|numeric|varchar|char|number)\s*\(|data_type:|not_null|nullable|::(date|timestamp|int|bigint|float)'
```
Run `dbt parse && dbt compile && dbt test` (gate on `command -v dbt`). Compare `target/manifest.json` before/after when available.

**Avro (.avsc)** — every added field: verify `"default"` present; every removed field or enum symbol: verify the field had `"default"` in the old schema (absence is FORWARD-INCOMPATIBLE under FULL/FORWARD mode); run Confluent Registry probe when `SCHEMA_REGISTRY_URL` set:
```sh
git diff "$BASE"...HEAD -- '*.avsc' | grep -E '^[+-]\s*"(name|type|default|symbols)"'
```
**Protobuf (.proto)** — any removed field-number line not in a `reserved` block is blocking; any field-number reused with a changed type is blocking:
```sh
git diff "$BASE"...HEAD -- '*.proto' | grep -E '^-\s+\w.*=\s*[0-9]+\s*;'
```
**AsyncAPI / CloudEvents** — diff channel/message schemas for narrowings; confirm CloudEvents `id`/`specversion`/`type`/`source` intact; flag missing version bump on breaking changes:
```sh
git diff "$BASE"...HEAD -- 'asyncapi.y*ml' 'asyncapi.json' '*.cloudevents.json'
```
**Consumer grep** — for every changed column/field name: `grep -rn '<name>'` across the repo to find downstream readers of the changed surface.

## 4. Blocking bar
Set blocking:true (cite file:line, before→after, and at least one downstream consumer) ONLY for:
- New Avro field without `"default"` — BACKWARD-INCOMPATIBLE per Avro spec; new readers cannot decode old records.
- Removed Avro field or enum symbol that lacked `"default"` in the old schema (FORWARD-INCOMPATIBLE; old readers cannot decode new records) with live consumers.
- Protobuf field number deleted (no `reserved`) or reused with a different wire type — silent deserialization corruption per Protobuf Language Guide.
- SQL/dbt column dropped, renamed, retyped, or narrowed (precision/scale/length/nullability) with active downstream consumers and no coordinated migration.
- AsyncAPI/CloudEvents required field removed or envelope type narrowed, no version bump, active consumers.
- Breaking shape change with semver MAJOR version unchanged and confirmed live consumers.
Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Column rename disguised as ADD + DROP in the same diff — `grep -E 'ADD COLUMN|DROP COLUMN'` on the same table name.
- Enum value removal from `ENUM(`, `accepted_values`, Avro `"symbols"`, or Protobuf enum — breaks all existing readers.
- `NOT NULL`/`required` added to an existing column with no backfill migration covering old rows.
- Protobuf field number deleted then re-added with a different type in the same diff.
- New Avro field without `"default"` — breaks BACKWARD compatibility for new readers.
- `dbt contract: enforced: true` removed from a model config to allow a breaking shape change through compile.
- `SELECT *` in downstream SQL consuming a model whose columns changed — silently absorbs renames and drops.
- `json_extract`/`jsonb_extract_path`/`get_json_object` with hardcoded key names referencing a renamed or removed field.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-contract-juror.json. ran[]/skipped[] honest. id = dc-<check>-<file>:<line>. Nothing outside the JSON.
