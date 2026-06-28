{{
    config(
        materialized = 'table'
    )
}}

with invoice_lines as (

    select * from {{ ref('fct_invoice_lines') }}

),

daily as (

    select
        invoice_date,
        currency_code,

        count(distinct invoice_id)              as invoice_count,
        count(*)                                as invoice_line_count,

        sum(line_amount)                        as billed_subtotal,
        sum(line_tax)                           as billed_tax,
        sum(allocated_invoice_discount)         as billed_discount,
        sum(invoice_total)                      as billed_total

    from invoice_lines

    group by 1, 2

)

select
    invoice_date,
    currency_code,
    invoice_count,
    invoice_line_count,
    billed_subtotal,
    billed_tax,
    billed_discount,
    billed_total

from daily
