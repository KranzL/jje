{{
  config(
    materialized='view'
  )
}}

with source as (
  select * from {{ source('logistics', 'shipments') }}
),

renamed as (
  select
    shipment_id,
    order_reference,
    carrier_code,
    service_level,
    ship_from_warehouse_id,
    shipment_status,
    tracking_number,
    cast(weight_grams as number(12, 0)) as weight_grams,
    shipped_at,
    delivered_at,
    to_date(shipped_at)                 as shipped_date
  from source
  where shipment_status != 'voided'
)

select * from renamed
