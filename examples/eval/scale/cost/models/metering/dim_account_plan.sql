{{ config(materialized='table') }}

with plans as (
  select
    account_id,
    plan_tier,
    monthly_request_quota,
    is_active,
    effective_from,
    effective_to
  from {{ source('billing', 'account_plans') }}
  where is_active = true
),

ranked as (
  select
    account_id,
    plan_tier,
    monthly_request_quota,
    effective_from,
    row_number() over (
      partition by account_id
      order by effective_from desc
    ) as rn
  from plans
)

select
  account_id,
  plan_tier,
  monthly_request_quota,
  effective_from
from ranked
where rn = 1
