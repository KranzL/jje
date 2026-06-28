-- migration: 0007_payment_events_evolve
-- engine: spark-sql (iceberg v2)
-- ticket: DATA-4472
--
-- Extends payment_events with settlement linkage and aligns the monetary
-- columns with the new shared decimal(18,x) house standard. The psp_ref
-- column is renamed to its canonical psp_reference name; Iceberg tracks
-- columns by field id so the rename is a metadata-only operation and prior
-- snapshots remain readable.

ALTER TABLE lake.payments.payment_events
    ALTER COLUMN amount_minor TYPE bigint;

ALTER TABLE lake.payments.payment_events
    ALTER COLUMN amount_minor COMMENT 'Authorized amount in minor units, widened from int';

ALTER TABLE lake.payments.payment_events
    RENAME COLUMN psp_ref TO psp_reference;

ALTER TABLE lake.payments.payment_events
    ALTER COLUMN captured_amount TYPE decimal(18,2);

ALTER TABLE lake.payments.payment_events
    ALTER COLUMN fee_amount TYPE decimal(18,4);

ALTER TABLE lake.payments.payment_events
    ADD COLUMN settlement_batch_id bigint COMMENT 'FK to settlement_batches, nullable until backfilled';

ALTER TABLE lake.payments.payment_events
    ADD COLUMN settlement_currency string COMMENT 'ISO 4217 settlement currency';

ALTER TABLE lake.payments.payment_events
    ADD COLUMN settled_at timestamp COMMENT 'Settlement timestamp in UTC';
