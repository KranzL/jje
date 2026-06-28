{{
    config(
        materialized = 'table'
    )
}}

with order_revenue as (

    select * from {{ ref('fct_order_revenue') }}

),

daily as (

    select
        order_date,
        currency_code,
        count(distinct order_id)    as order_count,
        sum(units_sold)             as units_sold,
        sum(net_revenue)            as net_revenue

    from order_revenue

    group by 1, 2

)

select * from daily
