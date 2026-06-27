with source as (
    select * from {{ ref('stg_customers') }}
)

select
    customer_id,
    full_name,
    email,
    lifetime_value
from source
