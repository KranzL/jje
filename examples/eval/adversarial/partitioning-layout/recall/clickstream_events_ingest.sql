CREATE TABLE IF NOT EXISTS lake.clickstream_events (
  user_id        BIGINT,
  session_id     STRING,
  page_url       STRING,
  referrer_url   STRING,
  user_agent     STRING,
  event_name     STRING,
  event_epoch_ms BIGINT
)
PARTITIONED BY (event_hour STRING)
STORED AS PARQUET
TBLPROPERTIES (
  'parquet.compression' = 'ZSTD',
  'parquet.block.size'  = '134217728'
);

SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;
SET hive.exec.max.dynamic.partitions = 100000;
SET hive.exec.max.dynamic.partitions.pernode = 100000;

INSERT INTO lake.clickstream_events PARTITION (event_hour)
SELECT
  s.user_id,
  s.session_id,
  s.page_url,
  s.referrer_url,
  s.user_agent,
  s.event_name,
  s.event_epoch_ms,
  from_unixtime(cast(s.event_epoch_ms / 1000 AS BIGINT), 'yyyyMMddHHmmss') AS event_hour
FROM staging.raw_clickstream s
WHERE s.event_epoch_ms IS NOT NULL
  AND s.event_name IN ('page_view', 'click', 'scroll', 'form_submit')
  AND s.user_id IS NOT NULL
DISTRIBUTE BY event_hour
SORT BY event_epoch_ms;
