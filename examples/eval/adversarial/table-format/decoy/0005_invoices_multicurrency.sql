-- Migration 0005: multi-currency support for lakehouse.billing.invoices
-- Owner: billing-platform
-- Context: amounts now carry four decimals to hold pre-rounding minor units,
--          and high-volume aggregator accounts overflowed the 32-bit line count.

ALTER TABLE lakehouse.billing.invoices
  SET TBLPROPERTIES (
    'delta.enableTypeWidening' = 'true'
  );

ALTER TABLE lakehouse.billing.invoices
  ADD COLUMNS (
    currency_code STRING COMMENT 'ISO 4217',
    fx_rate       DECIMAL(12,6)
  );

ALTER TABLE lakehouse.billing.invoices
  ALTER COLUMN line_count TYPE BIGINT;

ALTER TABLE lakehouse.billing.invoices
  ALTER COLUMN net_amount TYPE DECIMAL(12,4);

ALTER TABLE lakehouse.billing.invoices
  ALTER COLUMN tax_amount TYPE DECIMAL(12,4);
