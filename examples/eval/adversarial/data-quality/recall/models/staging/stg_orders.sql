with source as (

    select * from {{ source('shop', 'orders') }}

),

renamed as (

    select
        id                          as order_id,
        customer_id,
        status                      as order_status,
        currency_code,
        grand_total                 as order_total,
        ordered_at

    from source

)

select * from renamed
