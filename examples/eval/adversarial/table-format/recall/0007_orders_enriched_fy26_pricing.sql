-- Migration 0007: FY26 pricing rollout for lakehouse.sales.orders_enriched
-- Owner: revenue-data-eng
-- Context: finance needs sub-cent list prices and a few rollup attributes.
--          Enabling type widening so the line-count metric stops overflowing
--          on high-volume B2B orders.

ALTER TABLE lakehouse.sales.orders_enriched
  SET TBLPROPERTIES (
    'delta.enableTypeWidening' = 'true'
  );

ALTER TABLE lakehouse.sales.orders_enriched
  ADD COLUMNS (
    fulfillment_channel STRING COMMENT 'web | retail | partner',
    promo_code          STRING,
    is_gift             BOOLEAN
  );

ALTER TABLE lakehouse.sales.orders_enriched
  ALTER COLUMN order_line_count TYPE BIGINT;

ALTER TABLE lakehouse.sales.orders_enriched
  ALTER COLUMN unit_price TYPE DECIMAL(10,4);

ALTER TABLE lakehouse.sales.orders_enriched
  ALTER COLUMN unit_price COMMENT 'list price per unit (FY26 sub-cent pricing)';

ALTER TABLE lakehouse.sales.orders_enriched
  ALTER COLUMN fx_rate TYPE DECIMAL(12,6);
