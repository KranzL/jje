CREATE TABLE IF NOT EXISTS lake.transaction_events (
  txn_id      STRING,
  account_id  BIGINT,
  merchant_id BIGINT,
  amount      DECIMAL(18,2),
  currency    STRING,
  event_ts    TIMESTAMP
)
PARTITIONED BY (dt DATE, event_hour INT)
CLUSTERED BY (account_id) INTO 64 BUCKETS
STORED AS PARQUET
TBLPROPERTIES (
  'parquet.compression' = 'ZSTD',
  'parquet.block.size'  = '134217728'
);

SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;
SET hive.enforce.bucketing = true;

INSERT INTO lake.transaction_events PARTITION (dt, event_hour)
SELECT
  s.txn_id,
  s.account_id,
  s.merchant_id,
  s.amount,
  s.currency,
  s.event_ts,
  cast(s.event_ts AS DATE) AS dt,
  hour(s.event_ts)         AS event_hour
FROM staging.raw_transactions s
WHERE s.event_ts IS NOT NULL
  AND s.amount IS NOT NULL
  AND s.account_id IS NOT NULL
DISTRIBUTE BY cast(s.event_ts AS DATE), hour(s.event_ts);
