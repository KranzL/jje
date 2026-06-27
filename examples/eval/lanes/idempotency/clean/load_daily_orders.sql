MERGE INTO warehouse.fact_orders AS t
USING (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.amount
    FROM staging.orders_raw o
    WHERE o.order_date = CURRENT_DATE
) AS s
ON t.order_id = s.order_id
WHEN MATCHED THEN UPDATE SET
    t.customer_id = s.customer_id,
    t.order_date  = s.order_date,
    t.amount      = s.amount
WHEN NOT MATCHED THEN INSERT (order_id, customer_id, order_date, amount)
    VALUES (s.order_id, s.customer_id, s.order_date, s.amount);
