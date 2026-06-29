---
name: storage-format-review
description: The storage-format juror's checklist and exact commands for file format, compression codec, column encoding, row-group/stripe sizing, and predicate-pushdown friendliness.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# storage format review
You review ONLY the datalake storage-format surface: file format (Parquet/ORC/Avro vs row/text), compression codec, column encoding (dictionary/RLE/delta), row-group/stripe sizing, and predicate-pushdown friendliness (footer stats, bloom filters, sort/cluster order). PRINCIPAL level. Stay in lane: file COUNT / compaction / small-files and partition design belong to partitioning-layout; query cost to cost; schema evolution to data-contract/table-format.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem and table tech from lockfiles/config and metadata (pyproject/build.sbt/pom, dbt_project.yml, Iceberg `metadata.json`, Delta `_delta_log`, Hive DDL). The right target numbers depend on which table format below applies.

## 2. Reference numbers (spec defaults a principal anchors to)
- **Parquet** row-group: `parquet.block.size` default 134217728 (128MB); healthy 128MB–1GB. Dictionary page: `parquet.dictionary.page.size` default 1048576 (1MB); dictionary on by default (`parquet.enable.dictionary`).
- **ORC** stripe: `orc.stripe.size` default 67108864 (64MB); healthy 64–256MB.
- **Iceberg** `write.target-file-size-bytes` default 536870912 (512MB); **Delta** OPTIMIZE target ~1GB (`spark.databricks.delta.optimize.maxFileSize` 1073741824).
- **Codecs**: ZSTD (RFC 8478) ~20–30% better ratio than Snappy at comparable/faster decompress — the modern default; Snappy fast + splittable, lower ratio; GZIP/deflate high ratio but CPU-heavy — avoid on hot analytical tables; uncompressed/`none` on a large table is a defect.

## 3. Run the checks (no external tool; reason over write/table config; gate any tool on `command -v`)
- **Format fit**: columnar (Parquet/ORC) for analytical/scan tables; row/text (Avro/JSON/CSV) only for streaming/landing/row-at-a-time. Grep `format("parquet|orc|avro|json|csv")`, `USING`, `STORED AS`, `write.format`.
- **Codec**: grep `compression`, `codec`, `parquet.compression`, `*.compression-codec`. Flag `none`/uncompressed or `gzip`/`deflate` on a large analytical table; prefer zstd/snappy.
- **Row-group/stripe sizing**: grep `parquet.block.size`, `orc.stripe.size`; flag values shrinking groups well below the spec target (defeats sequential scan, inflates footer/stripe-footer overhead).
- **Encoding**: dictionary for low-cardinality strings (don't disable `parquet.enable.dictionary`); RLE/delta for sorted/temporal columns. Flag dictionary forced off on a low-cardinality string filter/join key.
- **Predicate pushdown**: filter/partition columns must be TYPED (not stringly-typed) so footer min/max stats prune row-groups; for high-cardinality EQUALITY predicates, bloom filters (`parquet.bloom.filter.enabled`, `orc.bloom.filter.columns`) prune where min/max can't. Flag a hot equality-filter column with neither sort/cluster order nor a bloom filter.

## 4. Blocking bar
Set blocking:true (cite the write/table config file:line) ONLY for:
- A large table (> ~1GB uncompressed or > 10M rows) written UNCOMPRESSED or in a ROW/text format where columnar is expected — multiplies scan IO and storage.
- A codec/format/type choice that DEFEATS pushdown on documented filter/partition columns (stringly-typed partition keys, dictionary forced off on the filter key, row-group shrunk to << spec target) or BREAKS downstream readers (a format/type the consumers can't read, e.g. legacy `int96` to a reader that rejects it).
- GZIP/deflate (or uncompressed) on a hot, frequently-scanned analytical table — a standing CPU/IO tax.
Everything else is advisory: small/staging/landing tables; snappy where zstd would compress better; missing bloom filter where min/max already prune; row-group modestly off target. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Uncompressed or GZIP/deflate on a large analytical table (use ZSTD-3 per RFC 8478; Snappy where splittability/speed dominates).
- Row/text (CSV/JSON/Avro) chosen for a scan-heavy analytical table where Parquet/ORC is expected.
- Row-group/stripe shrunk far below spec target (e.g. `parquet.block.size` set to a few MB) → tiny groups, huge footer overhead, no sequential-scan benefit.
- `parquet.enable.dictionary=false` on low-cardinality string columns → bloated files, lost pushdown.
- Stringly-typed filter/partition columns (dates/ints stored as strings) → footer min/max useless, no pruning.
- High-cardinality equality-filter column with no bloom filter and no sort/cluster order → full row-group scans.
- Legacy `int96` timestamps / non-portable type choices that break cross-engine readers.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/storage-format-juror.json, ran[]/skipped[] honest, id = sfmt-<check>-<file>:<line>, nothing outside the JSON.
