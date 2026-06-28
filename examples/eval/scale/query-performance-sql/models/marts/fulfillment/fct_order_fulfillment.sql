{{
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    cluster_by=['order_date']
  )
}}

with order_shipments as (
  select * from {{ ref('int_order_shipments') }}

  {% if is_incremental() %}
  where order_date >= (select dateadd('day', -7, max(order_date)) from {{ this }})
  {% endif %}
),

customers as (
  select
    customer_id,
    customer_segment,
    home_region_code
  from {{ ref('dim_customers') }}
),

enriched as (
  select
    os.order_id,
    os.customer_id,
    c.customer_segment,
    c.home_region_code,
    os.warehouse_id,
    os.fulfillment_channel,
    coalesce(os.service_level, 'standard')  as service_level,
    os.carrier_code,
    os.order_status,
    os.shipment_status,
    os.order_total_cents,
    os.currency_code,
    os.weight_grams,
    os.order_date,
    os.placed_at_utc,
    os.promised_ship_at,
    os.shipped_at,
    os.delivered_at,
    os.out_for_delivery_at,
    datediff('hour', os.placed_at_utc, os.shipped_at)        as hours_to_ship,
    datediff('hour', os.shipped_at, os.delivered_at)         as transit_hours,
    case
      when os.shipped_at is null then 'unshipped'
      when os.shipped_at <= os.promised_ship_at then 'on_time'
      else 'late'
    end                                                      as ship_sla_status,
    case
      when os.delivered_at is not null
       and to_date(os.delivered_at) = os.order_date then true
      else false
    end                                                      as same_day_delivered
  from order_shipments os
  left join customers c
    on os.customer_id = c.customer_id
)

select
  order_id,
  customer_id,
  customer_segment,
  home_region_code,
  warehouse_id,
  fulfillment_channel,
  service_level,
  carrier_code,
  order_status,
  shipment_status,
  order_total_cents,
  currency_code,
  weight_grams,
  order_date,
  placed_at_utc,
  promised_ship_at,
  shipped_at,
  delivered_at,
  hours_to_ship,
  transit_hours,
  ship_sla_status,
  same_day_delivered
from enriched
