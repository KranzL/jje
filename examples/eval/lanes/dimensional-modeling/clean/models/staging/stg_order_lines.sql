select
    order_id,
    line_number,
    product_id,
    quantity,
    unit_price
from {{ source('sales', 'order_lines') }}
