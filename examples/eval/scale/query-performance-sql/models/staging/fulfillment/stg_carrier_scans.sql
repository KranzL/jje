{{
  config(
    materialized='view'
  )
}}

with source as (
  select * from {{ source('logistics', 'carrier_scans') }}
),

renamed as (
  select
    scan_id,
    shipment_id,
    scan_type,
    scan_location_code,
    scanned_at,
    to_date(scanned_at) as scan_date
  from source
  where scan_type in ('picked_up', 'in_transit', 'out_for_delivery', 'delivered')
)

select * from renamed
