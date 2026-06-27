with events as (
    select * from {{ ref('stg_billing_events') }}
),

converted as (
    select
        invoice_line_id,
        invoice_id,
        product_sku,
        billing_country,
        quantity,
        list_price_local,
        discount_local,
        fx_rate_to_usd,
        list_price_local * fx_rate_to_usd               as gross_unit_price_usd,
        discount_local * fx_rate_to_usd                 as discount_usd
    from events
),

final as (
    select
        invoice_line_id,
        invoice_id,
        product_sku,
        billing_country,
        quantity,
        cast(discount_usd as decimal(18, 6))            as discount_usd,
        cast(gross_unit_price_usd as decimal(18, 6))    as gross_unit_price_usd,
        cast(round(gross_unit_price_usd, 2) as decimal(18, 2))
                                                        as gross_unit_price_usd_display,
        cast(
            (gross_unit_price_usd - discount_usd) * quantity
            as decimal(18, 6)
        )                                               as extended_amount_usd
    from converted
)

select * from final
