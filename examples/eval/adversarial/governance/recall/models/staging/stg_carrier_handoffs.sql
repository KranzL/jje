{{
    config(
        materialized='view',
        tags=['fulfillment', 'pii']
    )
}}

with source as (

    select * from {{ source('fulfillment', 'shipment_handoffs') }}

),

renamed as (

    select
        handoff_id,
        shipment_id,
        carrier_code,

        recipient_name,
        recipient_line1,
        recipient_postal,

        nullif(trim(lower(notify_at)), '')      as ext_ref,

        weight_grams,
        declared_value_minor,
        handed_off_at

    from source

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['handoff_id', 'carrier_code']) }} as handoff_key,
        handoff_id,
        shipment_id,
        carrier_code,
        recipient_name,
        recipient_line1,
        recipient_postal,
        ext_ref,
        weight_grams,
        declared_value_minor,
        handed_off_at

    from renamed
    where handed_off_at is not null

)

select * from final
