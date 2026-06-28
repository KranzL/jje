-- migration: 0008_settlement_batches_create
-- engine: spark-sql (iceberg v2)
-- ticket: DATA-4473

CREATE TABLE IF NOT EXISTS lake.payments.settlement_batches (
    settlement_batch_id   bigint        NOT NULL,
    provider              string        NOT NULL,
    settlement_currency   string        NOT NULL,
    opened_at             timestamp     NOT NULL,
    closed_at             timestamp,
    gross_amount          decimal(18,2) NOT NULL,
    fee_amount            decimal(18,2) NOT NULL,
    net_amount            decimal(18,2) NOT NULL,
    event_count           bigint        NOT NULL,
    status                string        NOT NULL,
    ingested_at           timestamp     NOT NULL
)
USING iceberg
PARTITIONED BY (days(opened_at), provider)
TBLPROPERTIES (
    'format-version' = '2',
    'write.parquet.compression-codec' = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max' = '50'
);

ALTER TABLE lake.payments.settlement_batches
    WRITE ORDERED BY (settlement_currency, opened_at);
