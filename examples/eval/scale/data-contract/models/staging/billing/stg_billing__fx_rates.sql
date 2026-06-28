with source as (
    select * from {{ source('billing', 'fx_rates') }}
),

renamed as (
    select
        upper(ccy)                          as currency_code,
        cast(as_of_date as date)            as rate_date,
        cast(usd_rate as numeric(18,8))     as rate_to_usd
    from source
    where usd_rate is not null
)

select
    currency_code,
    rate_date,
    rate_to_usd
from renamed
