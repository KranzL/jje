{{ config(materialized='view') }}

with source as (

    select * from {{ source('gateway', 'payment_event_log') }}

),

renamed as (

    select
        event_id,
        payment_id,
        order_id,
        lower(event_type)                               as event_type,
        cast(amount_minor as bigint)                    as amount_minor,
        upper(currency_code)                            as currency_code,
        cast(occurred_at as timestamp)                  as occurred_at,
        cast(_ingested_at as timestamp)                 as ingested_at
    from source
    where event_id is not null
      and payment_id is not null

)

select * from renamed
