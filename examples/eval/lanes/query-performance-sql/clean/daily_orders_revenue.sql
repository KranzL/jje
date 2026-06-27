{{ config(materialized='table') }}

select
    o.customer_id,
    count(*) as order_count,
    sum(o.amount) as gross_revenue
from {{ ref('fct_orders') }} as o
where o.event_ts >= '2026-06-25'
  and o.event_ts < '2026-06-26'
group by o.customer_id
