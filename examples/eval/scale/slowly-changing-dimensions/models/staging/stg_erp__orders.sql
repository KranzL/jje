with source as (

    select * from {{ source('erp', 'orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        product_id,
        order_status,
        cast(ordered_at as timestamp)     as ordered_at,
        cast(order_total as numeric(18,2)) as order_total,
        currency_code
    from source
    where order_id is not null
      and ordered_at is not null

)

select * from renamed
