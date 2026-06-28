with source as (

    select * from {{ source('billing', 'invoices') }}

),

renamed as (

    select
        invoice_id,
        account_id,
        subscription_id,
        billing_period_start::date      as billing_period_start,
        billing_period_end::date        as billing_period_end,
        invoice_date::date              as invoice_date,
        upper(currency_code)            as currency_code,
        invoice_status,
        is_credit_note,
        subtotal_amount                 as invoice_subtotal,
        discount_amount                 as invoice_discount,
        tax_amount                      as invoice_tax,
        total_amount                    as invoice_total

    from source

    where not coalesce(is_voided, false)

)

select * from renamed
