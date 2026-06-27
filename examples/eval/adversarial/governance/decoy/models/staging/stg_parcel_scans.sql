{{
    config(
        materialized='view',
        tags=['fulfillment', 'pii']
    )
}}

with source as (

    select * from {{ source('fulfillment', 'parcel_scans') }}

),

renamed as (

    select
        scan_id,
        shipment_id,
        carrier_code,

        recipient_name,
        recipient_postal,

        nullif(trim(upper(tracking_no)), '')     as ext_ref,

        scan_facility,
        scan_status,
        scanned_at

    from source

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['scan_id']) }} as scan_key,
        scan_id,
        shipment_id,
        carrier_code,
        recipient_name,
        recipient_postal,
        ext_ref,
        scan_facility,
        scan_status,
        scanned_at

    from renamed
    where scanned_at is not null

)

select * from final
