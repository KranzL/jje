---
name: catalog-metastore-ops-review
description: The catalog-metastore-ops juror's checklist for partition registration completeness, HMS/Glue pointer consistency, external-location coverage, migration cutover safety, Nessie branch isolation, and REST catalog endpoint agreement.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# catalog metastore ops review
You review ONLY the operational correctness of catalog entries and partition registration in Glue, HMS, Unity Catalog, Polaris, and Nessie: partition registration completeness after writes, catalog location/snapshot pointer consistency, external-location path coverage, cross-catalog migration cutover pattern, Nessie DDL branch targeting, and REST catalog endpoint agreement across engines. Stay in lane: lineage and PII classification to governance; scan cost to cost; file format to storage-format; schema evolution to data-contract/table-format.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect catalog tech: Terraform (.tf with aws_glue_catalog_table / databricks_sql_table / databricks_external_location), DDL (.sql, .hql), PySpark/Scala (.py, .scala), Iceberg metadata.json, Delta _delta_log, Nessie config (catalog.properties, iceberg.properties). Review only those files.

## 2. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding; reason over $CHANGED when live catalog access is unavailable)
- **Hive-style partition registration (HMS/Glue):** grep $CHANGED for `INSERT INTO|INSERT OVERWRITE|spark\.write|df\.write` targeting a partition-keyed table; every such path must be followed by `MSCK REPAIR TABLE`, `ALTER TABLE.*ADD PARTITION`, or a Glue `batch_create_partition` / `create_partition` SDK call; absent registration renders new partitions silently invisible to all downstream engines until a repair runs; if `command -v aws`, run `aws glue get-partitions --database-name <db> --table-name <tbl>` for tables named in $CHANGED.
- **Iceberg/Delta HMS-sync pointer consistency:** grep for `HiveTableOperations|catalog\.type=hive|aws_glue_catalog_table|metadata_location`; for Iceberg, confirm `Parameters.metadata_location` in the Glue entry exists and points to a reachable metadata.json; if `command -v aws`, run `aws glue get-table --database-name <db> --name <tbl>` and verify the `Parameters.metadata_location` value.
- **Unity Catalog / Polaris external location coverage:** grep $CHANGED for `CREATE.*TABLE.*LOCATION|CREATE EXTERNAL TABLE` and extract each `LOCATION` path; every such path must fall under a `databricks_external_location` Terraform resource or `CREATE EXTERNAL LOCATION` statement covering that prefix; a mismatch causes a runtime CREATE failure invisible at plan time; if `command -v databricks`, run `databricks tables get <catalog.schema.table>` for tables named in $CHANGED.
- **Cross-catalog migration cutover pattern:** grep $CHANGED for `DROP TABLE` within the same file or migration block as `CREATE TABLE|CREATE EXTERNAL TABLE` targeting the same table name; flag DROP+CREATE and require `ALTER TABLE.*SET LOCATION`, a catalog-copy, or a swap-and-verify step instead; DROP+CREATE destroys ACLs and table properties and opens a query-access outage during cutover.
- **Nessie DDL branch isolation:** grep for `nessie\.ref|catalog\.ref|NessieCatalog`; any DDL (CREATE TABLE, DROP TABLE, ALTER TABLE) in $CHANGED against a Nessie catalog must target a non-main ref (`nessie.ref` != `main`); a DDL commit directly to main is immediately visible to all production readers with no validation gate; if `command -v curl` and `NESSIE_ENDPOINT` is set, run `curl -sf "$NESSIE_ENDPOINT/api/v1/trees/tree/main/entries"` and cross-reference entries against DDL in $CHANGED.
- **REST catalog endpoint consistency:** grep $CHANGED for `spark\.sql\.catalog\.[^.]+\.uri|spark\.sql\.catalog\.[^.]+\.catalog-impl|catalog\.uri|catalog\.catalog-impl`; for every logical catalog name referenced by more than one engine config block in $CHANGED, verify `catalog-impl` and `uri` are byte-identical across all blocks; a mismatch produces two independent catalog views of the same underlying data with no error at write or read time.

## Blocking bar
Set blocking:true (cite file:line) ONLY for:
- A partition-producing write (INSERT/spark.write) on a Hive-partitioned table with no MSCK REPAIR, ADD PARTITION, or Glue partition SDK call in the changeset — new partitions are silently invisible.
- `aws glue get-table` confirms `Parameters.metadata_location` is absent, empty, or points to a path that does not exist for a Glue-synced Iceberg or Delta table.
- A `LOCATION` path in a UC or Polaris CREATE TABLE not covered by any external location visible in $CHANGED — guaranteed runtime CREATE failure.
- DROP+CREATE replacing an existing production table in a migration script — ACL wipe and query-access outage during cutover.
- `nessie.ref=main` (or `catalog.ref=main`) with DDL in the same changeset — immediate unvalidated production exposure.
- Two engine config blocks in $CHANGED with differing `catalog-impl` or `uri` for the same catalog name — silent catalog split-brain.
Everything else is advisory: REPAIR omitted on a non-partition table; LOCATION coverage unconfirmable from $CHANGED alone; nessie.ref=main with no DDL. A finding with no evidence is advisory by rule.

## Anti-patterns to hunt
- `spark.write`/`INSERT OVERWRITE` to a partition table with no `MSCK REPAIR TABLE` or `ALTER TABLE ADD PARTITION` in the same changeset.
- `aws_glue_catalog_table` Terraform block for an Iceberg table with no `parameters { metadata_location = "..." }` entry.
- `CREATE EXTERNAL TABLE ... LOCATION 's3://...'` with no `databricks_external_location` or `CREATE EXTERNAL LOCATION` covering that prefix.
- `DROP TABLE IF EXISTS <tbl>` immediately followed by `CREATE TABLE <tbl>` for the same table name in a migration script.
- `nessie.ref=main` or `catalog.ref=main` in a config file that also introduces DDL in the same changeset.
- `spark.sql.catalog.<name>.uri` differing between two engine config files for the same catalog name in $CHANGED.

## Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/catalog-metastore-ops-juror.json, ran[]/skipped[] honest, id = cat-<check>-<file>:<line>, nothing outside the JSON.
