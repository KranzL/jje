{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['event_date', 'event_hour'],
    file_format='delta',
    cluster_by=['account_id']
  )
}}

with events as (
  select
    device_id,
    session_id,
    event_name,
    event_ts,
    event_date,
    hour(event_ts)                                       as event_hour
  from {{ ref('int_telemetry__sessionized') }}

  {% if is_incremental() %}
  where event_date >= date_sub(current_date(), 3)
  {% endif %}
),

registry as (
  select device_id, account_id, platform
  from {{ ref('dim_device') }}
)

select
  e.event_date,
  e.event_hour,
  r.account_id,
  r.platform,
  count(*)                                              as event_count,
  count(distinct e.session_id)                          as session_count,
  count(distinct e.device_id)                           as active_devices,
  count(distinct e.event_name)                          as distinct_event_names
from events e
left join registry r
  on e.device_id = r.device_id
group by
  e.event_date,
  e.event_hour,
  r.account_id,
  r.platform
