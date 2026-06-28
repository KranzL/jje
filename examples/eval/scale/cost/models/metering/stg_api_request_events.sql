{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['dt'],
    file_format='delta',
    on_schema_change='append_new_columns'
  )
}}

with bounds as (
  select
    date_format(date_sub(current_date(), 3), 'yyyy-MM-dd') as window_start,
    date_format(date_sub(current_date(), 1), 'yyyy-MM-dd') as window_end
),

raw_events as (
  select
    e.request_id,
    e.account_id,
    e.endpoint_id,
    e.dt,
    cast(e.event_ts as timestamp)                         as event_ts,
    date_trunc('hour', cast(e.event_ts as timestamp))     as usage_hour,
    upper(e.http_method)                                  as http_method,
    cast(e.status_code as int)                            as status_code,
    coalesce(e.response_bytes, 0)                         as response_bytes,
    coalesce(e.latency_ms, 0)                             as latency_ms,
    e.api_key_hash
  from {{ source('raw', 'api_request_events') }} e
  cross join bounds b
  where e.dt between b.window_start and b.window_end
    and e.status_code is not null
    and e.account_id is not null
)

select
  request_id,
  account_id,
  endpoint_id,
  usage_hour,
  event_ts,
  http_method,
  status_code,
  response_bytes,
  latency_ms,
  api_key_hash,
  case when status_code >= 500 then 1 else 0 end as is_server_error,
  case when status_code = 429 then 1 else 0 end  as is_throttled,
  dt
from raw_events

{% if is_incremental() %}
where dt > (select coalesce(max(dt), '1970-01-01') from {{ this }})
{% endif %}
