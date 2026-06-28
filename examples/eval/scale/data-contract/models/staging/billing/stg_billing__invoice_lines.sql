with source as (
    select * from {{ source('billing', 'invoice_lines') }}
),

renamed as (
    select
        line_id                                  as invoice_line_id,
        inv_id                                   as invoice_id,
        prod_id                                  as product_id,
        qty                                      as quantity,
        cast(unit_price as numeric(18,4))        as unit_amount,
        cast(coalesce(discount, 0) as numeric(18,2)) as discount_amount,
        upper(currency)                          as transaction_currency_code,
        invoiced_at
    from source
    where line_id is not null
)

select
    invoice_line_id,
    invoice_id,
    product_id,
    quantity,
    unit_amount,
    discount_amount,
    transaction_currency_code,
    invoiced_at
from renamed
