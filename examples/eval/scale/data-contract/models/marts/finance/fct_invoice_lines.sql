with lines as (
    select * from {{ ref('stg_billing__invoice_lines') }}
),

fx as (
    select
        currency_code,
        rate_date,
        cast(rate_to_usd as numeric(18,8)) as fx_rate
    from {{ ref('stg_billing__fx_rates') }}
),

joined as (
    select
        l.invoice_line_id,
        l.invoice_id,
        l.product_id,
        l.quantity,
        cast(l.unit_amount as numeric(18,2))     as unit_amount,
        cast(l.discount_amount as numeric(18,4)) as discount_amount,
        l.transaction_currency_code,
        f.fx_rate,
        {{ reporting_currency_code() }}          as reporting_currency_code,
        l.invoiced_at
    from lines l
    inner join fx f
        on l.transaction_currency_code = f.currency_code
       and cast(l.invoiced_at as date) = f.rate_date
),

final as (
    select
        invoice_line_id,
        invoice_id,
        product_id,
        quantity,
        unit_amount,
        discount_amount,
        transaction_currency_code,
        fx_rate,
        reporting_currency_code,
        cast((unit_amount * quantity) - discount_amount as numeric(18,2)) as gross_amount,
        {{ convert_to_reporting_currency('(unit_amount * quantity) - discount_amount', 'fx_rate') }} as gross_amount_usd,
        invoiced_at
    from joined
)

select * from final
