with source as (

    select * from {{ source('billing', 'invoice_lines') }}

),

renamed as (

    select
        invoice_line_id,
        invoice_id,
        subscription_id,
        product_id,
        cast(quantity as integer)                   as quantity,
        cast(unit_amount_cents as numeric) / 100.0  as unit_amount,
        cast(amount_cents as numeric) / 100.0       as line_amount,
        cast(tax_cents as numeric) / 100.0          as tax_amount,
        cast(discount_cents as numeric) / 100.0     as discount_amount,
        cast(invoiced_at as date)                   as invoiced_on

    from source

)

select * from renamed
