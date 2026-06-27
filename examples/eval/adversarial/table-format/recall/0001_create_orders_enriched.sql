CREATE TABLE IF NOT EXISTS lakehouse.sales.orders_enriched (
  order_id        STRING    NOT NULL,
  customer_id     STRING    NOT NULL,
  order_ts        TIMESTAMP NOT NULL,
  order_line_count INT,
  unit_price      DECIMAL(10,2),
  order_total     DECIMAL(14,2),
  fx_rate         DECIMAL(9,6),
  ingest_date     DATE
)
USING DELTA
PARTITIONED BY (ingest_date)
TBLPROPERTIES (
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5',
  'delta.checkpoint.writeStatsAsStruct' = 'true'
);
