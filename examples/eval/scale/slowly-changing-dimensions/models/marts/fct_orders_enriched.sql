{{
    config(
        materialized='table'
    )
}}

with orders as (

    select * from {{ ref('stg_erp__orders') }}

),

fx_rates as (

    select
        currency_code,
        rate_to_usd,
        effective_from,
        coalesce(effective_to, cast('9999-12-31 23:59:59' as timestamp)) as effective_to
    from {{ source('fx', 'daily_rates') }}

),

orders_in_window as (

    select *
    from orders
    where ordered_at between cast('2022-01-01' as timestamp)
                         and cast('{{ var("reporting_through", "2099-12-31") }}' as timestamp)

),

customer_enriched as (

    select
        orders.order_id,
        orders.customer_id,
        orders.product_id,
        orders.order_status,
        orders.ordered_at,
        orders.order_total,
        orders.currency_code,
        cust.customer_history_key,
        cust.account_tier,
        cust.country_code,
        cust.sales_region_id
    from orders_in_window as orders
    left join {{ ref('dim_customer_history') }} as cust
        on  cust.customer_id = orders.customer_id
        and orders.ordered_at between cust.valid_from and cust.valid_to

),

events as (

    select * from customer_enriched

),

product_enriched as (

    select
        events.order_id,
        events.customer_id,
        events.product_id,
        events.order_status,
        events.ordered_at,
        events.order_total,
        events.currency_code,
        events.customer_history_key,
        events.account_tier,
        events.country_code,
        events.sales_region_id,
        dim.product_history_key,
        dim.category,
        dim.list_price
    from events
    {{ as_of_join(ref('dim_product_history'), 'product_id', 'ordered_at') }}

),

converted as (

    select
        product_enriched.*,
        round(product_enriched.order_total * fx_rates.rate_to_usd, 2) as order_total_usd
    from product_enriched
    left join fx_rates
        on  fx_rates.currency_code = product_enriched.currency_code
        and product_enriched.ordered_at >= fx_rates.effective_from
        and product_enriched.ordered_at <  fx_rates.effective_to

)

select
    order_id,
    customer_id,
    customer_history_key,
    product_id,
    product_history_key,
    order_status,
    account_tier,
    country_code,
    sales_region_id,
    category,
    list_price,
    ordered_at,
    order_total,
    currency_code,
    order_total_usd
from converted
