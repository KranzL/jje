{{
  config(
    materialized='table',
    cluster_by=['order_id']
  )
}}

with orders as (
  select
    order_id,
    customer_id,
    warehouse_id,
    fulfillment_channel,
    order_status,
    order_total_cents,
    currency_code,
    placed_at_utc,
    promised_ship_at,
    order_date
  from {{ ref('stg_orders') }}
  where placed_at_utc >= dateadd('day', -180, current_timestamp())
),

shipments as (
  select
    shipment_id,
    order_reference,
    carrier_code,
    service_level,
    ship_from_warehouse_id,
    shipment_status,
    weight_grams,
    shipped_at,
    delivered_at
  from {{ ref('stg_shipments') }}
),

last_scan as (
  select
    shipment_id,
    max(scanned_at) as last_scanned_at,
    max(case when scan_type = 'out_for_delivery' then scanned_at end) as out_for_delivery_at
  from {{ ref('stg_carrier_scans') }}
  group by shipment_id
),

joined as (
  select
    o.order_id,
    o.customer_id,
    o.warehouse_id,
    o.fulfillment_channel,
    o.order_status,
    o.order_total_cents,
    o.currency_code,
    o.placed_at_utc,
    o.promised_ship_at,
    o.order_date,
    s.shipment_id,
    s.carrier_code,
    s.service_level,
    s.shipment_status,
    s.weight_grams,
    s.shipped_at,
    s.delivered_at,
    sc.last_scanned_at,
    sc.out_for_delivery_at
  from orders o
  left join shipments s
    on cast(o.order_id as varchar) = s.order_reference
  left join last_scan sc
    on s.shipment_id = sc.shipment_id
)

select * from joined
