CREATE TABLE IF NOT EXISTS lakehouse.billing.invoices (
  invoice_id     STRING    NOT NULL,
  account_id     STRING    NOT NULL,
  issued_ts      TIMESTAMP NOT NULL,
  line_count     INT,
  net_amount     DECIMAL(10,2),
  tax_amount     DECIMAL(10,2),
  issued_date    DATE
)
USING DELTA
PARTITIONED BY (issued_date)
TBLPROPERTIES (
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5'
);
