{{ config(materialized='view') }}

with source as (

    select * from {{ source('gateway', 'settlement_batch') }}

),

renamed as (

    select
        settlement_id,
        cast(settled_on as date)                        as settled_on,
        cast(gross_minor as bigint)                     as gross_minor,
        cast(fee_minor as bigint)                       as fee_minor,
        cast(gross_minor - fee_minor as bigint)         as net_minor,
        upper(currency_code)                            as currency_code,
        cast(_ingested_at as timestamp)                 as ingested_at
    from source
    where settlement_id is not null

)

select * from renamed
