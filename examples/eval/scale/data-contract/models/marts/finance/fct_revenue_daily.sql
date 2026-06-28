with lines as (
    select * from {{ ref('fct_invoice_lines') }}
),

daily as (
    select
        cast(invoiced_at as date)        as revenue_date,
        reporting_currency_code,
        count(distinct invoice_id)       as invoice_count,
        sum(quantity)                    as units_sold,
        sum(gross_amount)                as gross_amount_txn,
        sum(gross_amount_usd)            as gross_amount_usd
    from lines
    group by 1, 2
)

select
    revenue_date,
    reporting_currency_code,
    invoice_count,
    units_sold,
    cast(gross_amount_txn as numeric(18,2)) as gross_amount_txn,
    cast(gross_amount_usd as numeric(18,4)) as gross_amount_usd
from daily
