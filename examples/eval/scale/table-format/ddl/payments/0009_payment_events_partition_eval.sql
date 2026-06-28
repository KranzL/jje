-- migration: 0009_payment_events_partition_evolve
-- engine: spark-sql (iceberg v2)
-- ticket: DATA-4474
--
-- Adds a settlement_batch_id bucket to the partition spec so settlement
-- backfills prune cleanly. Iceberg partition-spec evolution is additive and
-- applies to new data files only; historical files keep the old spec and
-- remain queryable.

ALTER TABLE lake.payments.payment_events
    ADD PARTITION FIELD bucket(32, settlement_batch_id) AS settlement_bucket;

ALTER TABLE lake.payments.payment_events
    SET TBLPROPERTIES (
        'read.split.target-size' = '134217728',
        'write.distribution-mode' = 'hash'
    );
