INSERT INTO warehouse.fact_orders
SELECT
    o.order_id,
    o.customer_id,
    o.order_date,
    o.amount
FROM staging.orders_raw o
WHERE o.order_date = CURRENT_DATE;
