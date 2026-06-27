{{ config(materialized='table') }}

select
    o.customer_id,
    count(*) as order_count,
    sum(o.amount) as gross_revenue
from {{ ref('fct_orders') }} as o
where date(o.event_ts) = '2026-06-25'
group by o.customer_id
