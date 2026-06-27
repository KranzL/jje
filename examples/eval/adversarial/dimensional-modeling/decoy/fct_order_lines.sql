{{
    config(
        materialized='incremental',
        unique_key='order_line_key',
        incremental_strategy='merge'
    )
}}

with order_lines as (

    select
        ol.order_line_id,
        ol.order_id,
        ol.product_id,
        ol.warehouse_id,
        ol.quantity_ordered,
        ol.quantity_shipped,
        ol.unit_list_price,
        ol.unit_sell_price,
        ol.line_discount_amount,
        ol.line_tax_amount,
        ol.line_created_at
    from {{ ref('stg_erp__order_lines') }} ol

    {% if is_incremental() %}
    where ol.line_created_at > (select max(line_created_at) from {{ this }})
    {% endif %}

),

orders as (

    select
        order_id,
        customer_id,
        order_status,
        order_currency_code,
        order_placed_at,
        freight_charge_amount
    from {{ ref('stg_erp__orders') }}

),

order_line_weights as (

    select
        order_id,
        order_line_id,
        (quantity_shipped * unit_sell_price) as line_extended_amount,
        sum(quantity_shipped * unit_sell_price)
            over (partition by order_id) as order_extended_amount
    from order_lines

),

products as (

    select
        product_id,
        product_key,
        standard_unit_cost
    from {{ ref('dim_product') }}

),

dates as (

    select date_key, calendar_date
    from {{ ref('dim_date') }}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['ol.order_line_id']) }} as order_line_key,

        d.date_key as order_date_key,
        p.product_key,
        ol.warehouse_id as warehouse_key,
        o.customer_id as customer_key,

        ol.order_id as order_number,
        ol.order_line_id as order_line_number,
        o.order_status,
        o.order_currency_code,

        ol.quantity_ordered,
        ol.quantity_shipped,
        ol.unit_list_price,
        ol.unit_sell_price,

        ol.quantity_shipped * ol.unit_sell_price as gross_line_amount,
        ol.line_discount_amount,
        ol.line_tax_amount,
        (ol.quantity_shipped * ol.unit_sell_price)
            - ol.line_discount_amount
            + ol.line_tax_amount as net_line_amount,

        ol.quantity_shipped * p.standard_unit_cost as line_cost_amount,

        case
            when w.order_extended_amount > 0
                then o.freight_charge_amount
                     * (w.line_extended_amount / w.order_extended_amount)
            else o.freight_charge_amount / count(*) over (partition by ol.order_id)
        end as allocated_freight_amount,

        ol.line_created_at
    from order_lines ol
    inner join orders o on ol.order_id = o.order_id
    inner join order_line_weights w on ol.order_line_id = w.order_line_id
    inner join products p on ol.product_id = p.product_id
    inner join dates d on cast(o.order_placed_at as date) = d.calendar_date

)

select * from final
