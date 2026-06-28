# Payments lakehouse schema evolution (DATA-447x)

This change set lands the settlement linkage work and standardizes the
payments monetary columns on the shared `decimal(18,x)` house types. All
payments tables are Iceberg v2.

## What ships

- `settlement_batches` is a new Iceberg table partitioned by
  `days(opened_at)` and `provider`.
- `payment_events` and `refund_events` gain `settlement_batch_id`,
  `settled_at`, and (on events) `settlement_currency`. All new columns are
  nullable and backfilled by a separate Spark job after these DDLs land.
- Monetary columns are widened to the `decimal(18,x)` standard.
- `psp_ref` is renamed to `psp_reference`. Iceberg identifies columns by
  field id, so the rename rewrites no data and old snapshots stay readable
  under time travel.
- `payment_events` gains an additive partition field on
  `bucket(32, settlement_batch_id)`.

## Evolution safety notes

Iceberg supports the following in place without rewriting data files:

- Widening integer types (`int` to `bigint`).
- Increasing `decimal` precision while keeping scale fixed.
- Renaming and reordering columns (field-id based).
- Adding optional columns.
- Additive partition-spec changes (new files only).

The `amount_minor` (`int` to `bigint`) and `captured_amount`
(`decimal(12,2)` to `decimal(18,2)`) changes fall in the supported set. The
migration runner validates each declared transition in `manifest.yaml`
against the live schema before applying the DDL.

## Rollout

1. Apply 0006 through 0009 in order via the migration runner.
2. Run `backfill_settlement_links` (separate ticket DATA-4480).
3. Flip the `settlement_v2` consumer flag once row counts reconcile.
