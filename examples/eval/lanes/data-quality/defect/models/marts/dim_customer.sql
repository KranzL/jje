select
    c.customer_id,
    c.customer_name,
    o.order_id,
    o.amount
from {{ ref('stg_customers') }} c
left join {{ ref('stg_orders') }} o
    on o.customer_id = c.customer_id
