---
name: storage-format-review
description: The storage-format juror's checklist and exact commands for file format, compression codec, column encoding, and predicate-pushdown friendliness.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# storage format review
You review ONLY the datalake storage format surface: file format (Parquet/ORC/Avro), compression codec, column encoding, row-group/stripe sizing, and predicate-pushdown friendliness. Stay in lane. Performance, cost, and schema evolution belong to other jurors.
## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem from lockfiles/config (go.mod, package.json, pyproject, Cargo.toml, dbt_project.yml, delta log, iceberg metadata).
## 2. Run the checks
Reason over the write/table config in the changed files. There is no external tool here; use concrete inspection patterns:
- File format: columnar (Parquet/ORC) for analytical tables vs row-oriented (Avro/JSON/CSV) where columnar is expected. Grep `format("parquet|orc|avro|json|csv")`, `USING`, `STORED AS`.
- Compression codec: snappy/zstd are good; `none`/uncompressed or gzip on huge tables is a problem. Grep `compression`, `codec`.
- Row-group / stripe sizing: grep `parquet.block.size`, `orc.stripe.size`, write options that shrink groups below readable size.
- Predicate pushdown / column pruning: confirm filter and partition columns are typed (not stringly-typed) and ordered so readers can skip. Inspect write options and column types.
## 3. Blocking bar
Set blocking:true ONLY for: a large table written uncompressed or in a row-oriented format where columnar is expected, or a format/type choice that defeats predicate pushdown on filter/partition columns or breaks downstream readers. Cite the table/write config. Small or staging tables are advisory. Everything else advisory; a finding with no evidence is advisory by rule.
## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/storage-format-juror.json, ran[]/skipped[] honest, id = sfmt-<check>-<file>:<line>, nothing outside the JSON.
