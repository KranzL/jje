-- migration: 0006_refunds_widen_amounts
-- engine: spark-sql (iceberg v2)
-- ticket: DATA-4471

ALTER TABLE lake.payments.refund_events
    ALTER COLUMN refund_amount TYPE decimal(18,2);

ALTER TABLE lake.payments.refund_events
    ALTER COLUMN refund_amount COMMENT 'Refunded amount in account currency, widened from decimal(12,2)';

ALTER TABLE lake.payments.refund_events
    ALTER COLUMN gateway_fee TYPE decimal(18,2);

ALTER TABLE lake.payments.refund_events
    ADD COLUMN settlement_batch_id bigint COMMENT 'FK to settlement_batches, nullable until backfilled';

ALTER TABLE lake.payments.refund_events
    ADD COLUMN settled_at timestamp COMMENT 'Settlement timestamp in UTC';
