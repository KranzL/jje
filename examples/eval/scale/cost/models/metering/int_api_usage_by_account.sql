{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['dt'],
    file_format='delta'
  )
}}

with events as (
  select
    account_id,
    endpoint_id,
    usage_hour,
    http_method,
    status_code,
    response_bytes,
    latency_ms,
    is_server_error,
    is_throttled,
    dt
  from {{ ref('stg_api_request_events') }}

  {% if is_incremental() %}
  where dt >= date_format(date_sub(current_date(), 2), 'yyyy-MM-dd')
  {% endif %}
),

per_account as (
  select
    account_id,
    usage_hour,
    count(*)                                       as request_count,
    count(distinct endpoint_id)                    as distinct_endpoints,
    sum(response_bytes)                            as total_response_bytes,
    sum(is_server_error)                           as server_errors,
    sum(is_throttled)                              as throttled_requests,
    sum(case when status_code < 400 then 1 else 0 end) as success_count,
    approx_percentile(latency_ms, 0.95)            as p95_latency_ms,
    dt
  from events
  group by account_id, usage_hour, dt
)

select
  account_id,
  usage_hour,
  request_count,
  distinct_endpoints,
  total_response_bytes,
  server_errors,
  throttled_requests,
  success_count,
  round(success_count / nullif(request_count, 0), 4) as success_rate,
  p95_latency_ms,
  dt
from per_account
