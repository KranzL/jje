{{ config(materialized='table') }}

with order_lines as (
    select * from {{ ref('stg_order_lines') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['ol.order_id', 'ol.line_number']) }} as order_line_sk,
    dd.date_key as order_date_key,
    dc.customer_sk,
    dp.product_sk,
    ol.order_id,
    ol.line_number,
    ol.quantity,
    ol.unit_price,
    ol.quantity * ol.unit_price as line_extended_amount,
    o.order_total
from order_lines ol
inner join orders o
    on ol.order_id = o.order_id
inner join {{ ref('dim_date') }} dd
    on o.order_date = dd.full_date
inner join {{ ref('dim_customer') }} dc
    on o.customer_id = dc.customer_id
inner join {{ ref('dim_product') }} dp
    on ol.product_id = dp.product_id
