{{
    config(
        materialized = 'table'
    )
}}

with invoice_lines as (

    select * from {{ ref('stg_billing__invoice_lines') }}

),

invoices as (

    select * from {{ ref('stg_billing__invoices') }}

),

plans as (

    select * from {{ ref('dim_subscription_plan') }}
    where is_current

),

line_weight as (

    select
        invoice_id,
        sum(line_amount) as invoice_line_amount_total

    from invoice_lines

    group by 1

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['invoice_lines.invoice_line_id']) }} as invoice_line_key,
        invoice_lines.invoice_line_id,
        invoice_lines.invoice_id,
        invoices.account_id,
        invoices.subscription_id,
        plans.plan_version_key,
        invoice_lines.product_id,
        invoice_lines.line_type,
        invoices.invoice_status,
        invoices.currency_code,
        invoices.billing_period_start,
        invoices.billing_period_end,
        invoices.invoice_date,

        invoice_lines.quantity,
        invoice_lines.unit_price,
        invoice_lines.line_amount,
        invoice_lines.line_tax,

        invoices.invoice_discount
            * (invoice_lines.line_amount
                / nullif(line_weight.invoice_line_amount_total, 0))     as allocated_invoice_discount,

        invoices.invoice_total

    from invoice_lines

    left join invoices
        on invoice_lines.invoice_id = invoices.invoice_id

    left join line_weight
        on invoice_lines.invoice_id = line_weight.invoice_id

    left join plans
        on invoice_lines.plan_id = plans.plan_id

)

select * from final
