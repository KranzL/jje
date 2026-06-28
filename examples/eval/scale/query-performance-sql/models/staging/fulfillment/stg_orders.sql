{{
  config(
    materialized='view'
  )
}}

with source as (
  select * from {{ source('commerce', 'orders') }}
),

renamed as (
  select
    order_id,
    customer_id,
    warehouse_id,
    order_status,
    fulfillment_channel,
    cast(order_total_cents as number(18, 0)) as order_total_cents,
    upper(currency_code)                      as currency_code,
    placed_at,
    promised_ship_at,
    cancelled_at,
    convert_timezone('UTC', placed_at)        as placed_at_utc,
    to_date(placed_at)                        as order_date
  from source
  where order_status not in ('draft', 'payment_failed')
)

select * from renamed
