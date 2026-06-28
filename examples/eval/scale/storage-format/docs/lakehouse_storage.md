# Lakehouse curated storage

This change moves the curated activity tables onto a config-driven writer so that
storage layout (format, compression, partitioning, file sizing) lives next to each
table instead of being hand-coded in every job.

## Writer

`pipelines/lakehouse/writers/parquet_writer.py` reads a `TableWriteConfig` and applies:

- declared column schema (via `schema.py`)
- partition columns
- within-partition sort order
- compression codec (defaults to `zstd` for columnar formats)
- format-specific writer options

## Tables in scope

| table | format | grain | dominant access pattern |
| --- | --- | --- | --- |
| `events_activity_fact` | parquet | one row per product event | time-range scans on `event_time` inside an `ingest_date` partition |
| `sessions_daily_agg` | parquet | account x session_date | window scans on `window_start` |
| `dim_merchant` | json | one row per merchant | full read, broadcast joined |
| `raw_app_events` | parquet | landing fidelity copy | replayed by ingest_date, never filtered on attributes |

`events_activity_fact` is the largest curated table (multiple billions of rows per
month). Analyst and BI queries almost always pin a single `ingest_date` partition and
then narrow to a sub-window, for example:

```sql
select account_id, event_type, count(*)
from events_activity_fact
where ingest_date = date '2026-06-20'
  and event_time >= '2026-06-20 14:00:00'
  and event_time <  '2026-06-20 15:00:00'
group by account_id, event_type
```

`dim_merchant` stays JSON on purpose: it is a few thousand rows, refreshed daily, and
always broadcast, so columnar layout and compression buy nothing and JSON keeps it
debuggable.

`raw_app_events` keeps every field as a string. It is the schema-on-read landing zone;
typing happens downstream in `build_events_activity_fact`, and nothing queries its
attributes directly.
