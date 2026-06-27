CREATE TABLE lakehouse.finance.payments (
    payment_id   bigint,
    customer_id  bigint,
    amount       bigint,
    currency     string,
    captured_at  timestamp
)
USING iceberg
PARTITIONED BY (days(captured_at))
TBLPROPERTIES (
    'format-version' = '2',
    'write.distribution-mode' = 'hash'
);

ALTER TABLE lakehouse.finance.payments ALTER COLUMN amount TYPE int;
