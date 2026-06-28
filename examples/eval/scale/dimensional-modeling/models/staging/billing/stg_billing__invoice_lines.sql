with source as (

    select * from {{ source('billing', 'invoice_lines') }}

),

renamed as (

    select
        invoice_line_id,
        invoice_id,
        product_id,
        plan_id,
        line_type,
        description                     as line_description,
        quantity,
        unit_price,
        line_discount_amount            as line_discount,
        line_tax_amount                 as line_tax,
        extended_amount                 as line_amount

    from source

)

select * from renamed
