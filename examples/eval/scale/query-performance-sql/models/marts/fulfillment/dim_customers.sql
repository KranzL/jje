{{
  config(
    materialized='table',
    cluster_by=['customer_id']
  )
}}

with source as (
  select * from {{ source('commerce', 'customers') }}
),

cleaned as (
  select
    customer_id,
    lower(trim(email))                       as email,
    customer_segment,
    upper(home_region_code)                  as home_region_code,
    cast(loyalty_points as number(12, 0))    as loyalty_points,
    created_at,
    to_date(created_at)                      as signup_date
  from source
  where customer_id is not null
)

select * from cleaned
