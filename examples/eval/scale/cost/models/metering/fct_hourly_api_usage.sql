{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['dt'],
    file_format='delta',
    cluster_by=['account_id']
  )
}}

with usage as (
  select
    account_id,
    usage_hour,
    request_count,
    distinct_endpoints,
    total_response_bytes,
    server_errors,
    throttled_requests,
    success_count,
    success_rate,
    p95_latency_ms,
    dt
  from {{ ref('int_api_usage_by_account') }}

  {% if is_incremental() %}
  where dt >= date_format(date_sub(current_date(), 2), 'yyyy-MM-dd')
  {% endif %}
),

plans as (
  select
    account_id,
    plan_tier,
    monthly_request_quota
  from {{ ref('dim_account_plan') }}
)

select
  u.account_id,
  p.plan_tier,
  u.usage_hour,
  to_date(u.usage_hour)                                       as usage_date,
  hour(u.usage_hour)                                          as usage_hour_of_day,
  u.request_count,
  u.distinct_endpoints,
  u.total_response_bytes,
  u.server_errors,
  u.throttled_requests,
  u.success_count,
  u.success_rate,
  u.p95_latency_ms,
  p.monthly_request_quota,
  round(u.request_count / nullif(p.monthly_request_quota, 0), 6) as quota_fraction_used,
  u.dt
from usage u
left join plans p
  on u.account_id = p.account_id
