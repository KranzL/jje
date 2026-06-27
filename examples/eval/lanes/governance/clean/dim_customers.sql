{{ config(materialized='table') }}

select
    customer_id,
    email,
    signup_date,
    country_code
from {{ source('crm', 'customers') }}
