with lines as (
    select * from {{ ref('fct_invoice_lines') }}
),

settlement as (
    select
        billing_country,
        product_sku,
        sum(quantity)                                       as units_settled,
        sum(gross_unit_price_usd * quantity)                as gross_settlement_usd,
        sum(extended_amount_usd)                            as net_settlement_usd
    from lines
    group by 1, 2
)

select * from settlement
