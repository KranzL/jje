{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['dt'],
    file_format='delta'
  )
}}

with source as (
  select
    event_id,
    device_id,
    session_id,
    event_name,
    event_ts,
    _ingested_at,
    payload,
    dt
  from {{ source('raw', 'device_telemetry_events') }}

  {% if is_incremental() %}
  where dt >= date_format(date_sub(current_date(), 3), 'yyyy-MM-dd')
  {% endif %}
),

cleaned as (
  select
    event_id,
    device_id,
    session_id,
    lower(trim(event_name))                              as event_name,
    cast(event_ts as timestamp)                          as event_ts,
    cast(_ingested_at as timestamp)                       as ingested_at,
    payload,
    dt
  from source
  where event_id is not null
    and device_id is not null
    and session_id is not null
)

select
  event_id,
  device_id,
  session_id,
  event_name,
  event_ts,
  ingested_at,
  payload,
  dt
from cleaned
