{{
    config(
        materialized = 'table'
    )
}}

with invoice_lines as (

    select * from {{ ref('stg_billing__invoice_lines') }}

),

subscriptions as (

    select * from {{ ref('stg_billing__subscriptions') }}

),

joined as (

    select
        {{ dbt_utils.generate_surrogate_key(['il.invoice_line_id']) }}  as invoice_line_key,
        il.invoice_line_id,
        il.invoice_id,
        il.subscription_id,
        s.account_id,
        s.plan_id,
        il.product_id,
        il.invoiced_on,
        s.status                    as subscription_status,
        s.seat_count                as subscription_seats,
        s.mrr_amount                as subscription_mrr,
        il.quantity,
        il.unit_amount,
        il.line_amount,
        il.tax_amount,
        il.discount_amount,
        il.line_amount + il.tax_amount - il.discount_amount  as net_line_amount

    from invoice_lines il
    inner join subscriptions s
        on il.subscription_id = s.subscription_id

)

select * from joined
