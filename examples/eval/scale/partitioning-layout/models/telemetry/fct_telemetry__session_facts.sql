{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['session_start_second'],
    file_format='delta',
    cluster_by=['device_id']
  )
}}

with sessions as (
  select
    session_id,
    device_id,
    min(session_start_ts)                                as session_start_ts,
    max(session_end_ts)                                  as session_end_ts,
    count(*)                                             as event_count,
    count(distinct event_name)                           as distinct_event_names,
    max(event_date)                                      as event_date
  from {{ ref('int_telemetry__sessionized') }}

  {% if is_incremental() %}
  where event_date >= date_sub(current_date(), 3)
  {% endif %}

  group by session_id, device_id
),

registry as (
  select
    device_id,
    account_id,
    platform
  from {{ ref('dim_device') }}
)

select
  s.session_id,
  s.device_id,
  r.account_id,
  r.platform,
  s.session_start_ts,
  s.session_end_ts,
  unix_timestamp(s.session_end_ts) - unix_timestamp(s.session_start_ts) as session_duration_s,
  s.event_count,
  s.distinct_event_names,
  to_date(s.session_start_ts)                            as session_date,
  hour(s.session_start_ts)                               as session_start_hour,
  date_trunc('second', s.session_start_ts)              as session_start_second
from sessions s
left join registry r
  on s.device_id = r.device_id
