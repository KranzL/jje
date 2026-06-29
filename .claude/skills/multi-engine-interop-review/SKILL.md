---
name: multi-engine-interop-review
description: The multi-engine-interop juror's checklist for Delta/Iceberg protocol version and feature-flag compatibility against declared reader/writer engines, plus concurrent multi-writer commit safety.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# multi-engine interop review
You review ONLY cross-engine compatibility: Delta/Iceberg protocol versions, feature-flag-to-engine version constraints, engine-specific vs portable table properties, and concurrent multi-writer commit safety. PRINCIPAL level. Stay in lane: schema evolution belongs to table-format; partition design belongs to partitioning-layout; file sizing belongs to storage-format.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect Delta (`_delta_log/`, protocol JSON with `minReaderVersion`) and Iceberg (`metadata.json` with `format-version`) artifacts in `$CHANGED`. Also scan cluster configs, Terraform engine configs, job manifests, `requirements*.txt`, and `pyproject.toml` for declared engine names and versions. Review only those files.

## 2. Compatibility reference (anchor all decisions here)
- **Delta protocol versions**: deletion vectors require `minReaderVersion 3`; column mapping requires `minReaderVersion 2` / `minWriterVersion 5`; liquid clustering requires `minReaderVersion 3` / `minWriterVersion 7`.
- **Iceberg format-version 2**: equality deletes (`content: 2` in manifest entries) are invisible to a Trino version lacking Iceberg equality-delete read support (stale rows returned, no error). Position deletes are version-gated in Flink; confirm declared Flink version supports them. Hive 3.x via `HiveIcebergStorageHandler` does not support equality deletes or all partition transform types.
- **Reader-incompatible Delta writer features**: `delta.feature.allowColumnDefaults` is an OSS Delta 3.0+ writer feature that reader engines lacking column-default support (Trino, Presto, DeltaKernel-standalone) do not evaluate; `delta.tuneFileSizesForRewrites` is a Databricks tuning property with no OSS effect. The risk is a declared reader that cannot honor the feature.
- **Iceberg multi-writer locking**: concurrent writers (e.g. Spark batch + Flink streaming) on the same Iceberg table using the Hadoop catalog against non-atomic object stores (e.g. S3 without atomic rename) silently drop commits under OCC conflict; REST, JDBC, and HMS catalog OCC raises CommitFailedException to the losing writer.

## 3. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding)
- **Delta protocol feature gating**: grep `_delta_log` protocol entries for `"minReaderVersion"`, `"minWriterVersion"`, `"deletionVectors"`, `"columnMapping"`, `"liquidClustering"`. Cross-reference each enabled feature's required version against every declared reader engine in `$CHANGED`. Flag any mismatch per the reference numbers in section 2.
- **Iceberg v2 MOR against reader versions**: grep `metadata.json` for `"format-version": 2`. Grep job/Flink configs and Hive DDL for `equality-delete`, `position-delete`, `merge-on-read`, `MOR`. Flag equality deletes when a Trino version lacking Iceberg equality-delete read support is declared; flag position deletes when the declared Flink version cannot be confirmed to support them; flag both when Hive 3.x is declared via `HiveIcebergStorageHandler`.
- **Reader-incompatible Delta writer features**: grep DDL, table-property blocks, and Terraform `delta_table` resources for `delta.feature.allowColumnDefaults`, `delta.tuneFileSizesForRewrites`. Flag when `$CHANGED` declares a reader engine that does not evaluate the feature (Trino/Presto/DeltaKernel-standalone for column defaults).
- **Concurrent multi-writer locking (Iceberg)**: grep job and cluster configs for two or more distinct engine writers (`spark`+`flink`, batch+streaming) targeting the same Iceberg table identifier using the Hadoop catalog. Require `lock.impl` set to a DynamoDB lock manager, JDBC lock manager, or the Iceberg REST catalog when the catalog is Hadoop on a non-atomic object store. Flag its absence.
- **Hive StorageHandler + Iceberg v2**: grep HMS DDL and hive-site configs for `HiveIcebergStorageHandler`. Flag `format-version: 2` tables registered in HMS when Hive 3.x is a declared reader.

## 4. Blocking bar
Set `blocking: true` (cite `file:line`) ONLY for:
- A Delta feature (`deletionVectors`, `columnMapping`, `liquidClustering`) active at a `minReaderVersion`/`minWriterVersion` that a declared reader engine cannot meet — produces wrong or silently missing rows.
- Iceberg format-version 2 equality deletes declared against a Trino version lacking Iceberg equality-delete read support or Hive 3.x via `HiveIcebergStorageHandler` — stale rows returned silently.
- Two or more engines writing to the same Iceberg table via the Hadoop catalog on a non-atomic object store with no `lock.impl` configured — silent commit loss under OCC.
- A Delta writer feature (e.g. `allowColumnDefaults`) set on a table whose declared reader engines cannot evaluate it, where the behavioral divergence is load-bearing.
Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `"format-version": 2` + Flink or Hive MOR writes + a Trino version lacking Iceberg equality-delete read support declared as a reader.
- `delta.feature.allowColumnDefaults` (or `delta.tuneFileSizesForRewrites`) alongside a declared reader engine that does not evaluate the feature.
- Spark + Flink writers targeting the same Iceberg table path via the Hadoop catalog on a non-atomic object store with no `lock.impl` or REST catalog locking configured.
- `HiveIcebergStorageHandler` registered against a `format-version: 2` table with equality deletes or non-identity partition transforms.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/multi-engine-interop-juror.json, ran[]/skipped[] honest, id = meng-<check>-<file>:<line>, nothing outside the JSON.
