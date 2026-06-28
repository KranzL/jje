{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['dt'],
    file_format='delta'
  )
}}

with bounds as (
  select
    date_sub(current_date(), 7) as window_start,
    date_sub(current_date(), 1) as window_end
),

scoped as (
  select
    e.endpoint_id,
    e.dt,
    date_trunc('hour', cast(e.event_ts as timestamp)) as usage_hour,
    cast(e.status_code as int)                        as status_code,
    coalesce(e.latency_ms, 0)                         as latency_ms,
    coalesce(e.response_bytes, 0)                     as response_bytes
  from {{ source('raw', 'api_request_events') }} e
  cross join bounds b
  where date(e.dt) between b.window_start and b.window_end
    and e.endpoint_id is not null
    and e.latency_ms is not null
),

graded as (
  select
    endpoint_id,
    usage_hour,
    count(*)                                  as sample_count,
    avg(latency_ms)                           as avg_latency_ms,
    approx_percentile(latency_ms, 0.50)       as p50_latency_ms,
    approx_percentile(latency_ms, 0.95)       as p95_latency_ms,
    approx_percentile(latency_ms, 0.99)       as p99_latency_ms,
    max(latency_ms)                           as max_latency_ms,
    sum(case when status_code >= 500 then 1 else 0 end) as server_errors,
    dt
  from scoped
  group by endpoint_id, usage_hour, dt
)

select
  endpoint_id,
  usage_hour,
  sample_count,
  round(avg_latency_ms, 2) as avg_latency_ms,
  p50_latency_ms,
  p95_latency_ms,
  p99_latency_ms,
  max_latency_ms,
  server_errors,
  dt
from graded
