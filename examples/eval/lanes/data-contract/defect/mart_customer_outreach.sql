select
    customer_id,
    email,
    lifetime_value
from {{ ref('dim_customers') }}
where lifetime_value > 1000
