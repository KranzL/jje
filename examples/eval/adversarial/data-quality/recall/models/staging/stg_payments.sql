with source as (

    select * from {{ source('shop', 'payments') }}

),

renamed as (

    select
        id                          as payment_id,
        order_id,
        method                      as payment_method,
        gateway,
        amount,
        captured_at

    from source

    where status = 'captured'

)

select * from renamed
