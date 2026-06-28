{{
    config(
        materialized = 'table'
    )
}}

with orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

rep_assignments as (

    select * from {{ ref('stg_rep_assignments') }}

),

regions as (

    select * from {{ ref('stg_regions') }}

),

item_rollup as (

    select
        order_id,
        count(*)                    as line_item_count,
        sum(quantity)               as units_sold,
        sum(line_total)             as gross_line_amount

    from order_items

    group by 1

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['orders.order_id', 'rep_assignments.sales_rep_id']) }} as order_revenue_key,
        orders.order_id,
        orders.customer_id,
        orders.order_status,
        orders.currency_code,
        orders.order_date,
        regions.region_name,
        regions.sales_territory,
        rep_assignments.sales_rep_id,
        rep_assignments.rep_name,
        item_rollup.line_item_count,
        item_rollup.units_sold,
        orders.order_total,
        orders.net_revenue

    from orders

    left join item_rollup
        on orders.order_id = item_rollup.order_id

    left join regions
        on orders.region_id = regions.region_id

    left join rep_assignments
        on orders.order_id = rep_assignments.order_id

)

select * from final
