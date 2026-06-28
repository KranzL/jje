with source as (

    select * from {{ source('shop', 'order_items') }}

),

renamed as (

    select
        id                          as order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        quantity * unit_price       as line_total

    from source

)

select * from renamed
