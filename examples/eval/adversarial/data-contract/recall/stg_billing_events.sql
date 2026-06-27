with source as (
    select * from {{ source('billing', 'invoice_line_events') }}
),

typed as (
    select
        invoice_line_id,
        invoice_id,
        product_sku,
        billing_country,
        cast(quantity as integer)                       as quantity,
        cast(list_price_local as decimal(18, 6))        as list_price_local,
        cast(discount_local as decimal(10, 2))          as discount_local,
        cast(fx_rate_to_usd as decimal(18, 8))          as fx_rate_to_usd,
        cast(occurred_at as timestamp)                  as occurred_at
    from source
)

select * from typed
