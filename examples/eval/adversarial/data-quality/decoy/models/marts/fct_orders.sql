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

ranked_payments as (

    select
        order_id,
        payment_id,
        payment_method,
        gateway,
        row_number() over (
            partition by order_id
            order by captured_at desc, payment_id desc
        ) as capture_rank

    from payments

),

primary_payment as (

    select
        order_id,
        payment_method,
        gateway

    from ranked_payments

    where capture_rank = 1

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['orders.order_id']) }} as order_key,
        orders.order_id,
        orders.customer_id,
        orders.order_status,
        orders.currency_code,
        orders.order_total,
        order_payments.amount_captured,
        order_payments.capture_count,
        primary_payment.payment_method,
        primary_payment.gateway,
        orders.ordered_at

    from orders

    left join order_payments
        on orders.order_id = order_payments.order_id

    left join primary_payment
        on orders.order_id = primary_payment.order_id

)

select * from final
