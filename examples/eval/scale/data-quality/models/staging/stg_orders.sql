with source as (

    select * from {{ source('shop', 'orders') }}

),

renamed as (

    select
        id                          as order_id,
        customer_id,
        region_id,
        status                      as order_status,
        currency_code,
        grand_total                 as order_total,
        discount_total,
        grand_total - discount_total as net_revenue,
        ordered_at,
        cast(ordered_at as date)    as order_date

    from source

    where status not in ('cancelled', 'fraud_hold')

)

select * from renamed
