{{
    config(
        materialized = 'table'
    )
}}

with orders as (

    select * from {{ ref('stg_orders') }}

),

payments as (

    select * from {{ ref('stg_payments') }}

),

order_payments as (

    select
        order_id,
        sum(amount)                 as amount_captured,
        count(*)                    as capture_count

    from payments

    group by 1

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['orders.order_id', 'payments.payment_id']) }} as order_key,
        orders.order_id,
        orders.customer_id,
        orders.order_status,
        orders.currency_code,
        orders.order_total,
        order_payments.amount_captured,
        order_payments.capture_count,
        payments.payment_method,
        payments.gateway,
        orders.ordered_at

    from orders

    left join order_payments
        on orders.order_id = order_payments.order_id

    left join payments
        on orders.order_id = payments.order_id

)

select * from final
