{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['event_date'],
    file_format='delta'
  )
}}

with source as (
  select
    event_id,
    creator_id,
    viewer_id,
    session_id,
    video_id,
    device_type,
    country_code,
    event_type,
    watch_ms,
    buffer_ms,
    bitrate_kbps,
    event_ts
  from {{ source('playback', 'raw_playback_events') }}

  {% if is_incremental() %}
  where event_ts >= (select coalesce(max(event_ts), '1970-01-01') from {{ this }})
  {% endif %}
),

cleaned as (
  select
    event_id,
    creator_id,
    viewer_id,
    session_id,
    video_id,
    lower(device_type)                                  as device_type,
    upper(country_code)                                 as country_code,
    event_type,
    cast(watch_ms as bigint)                            as watch_ms,
    cast(buffer_ms as bigint)                           as buffer_ms,
    cast(bitrate_kbps as int)                           as bitrate_kbps,
    event_ts,
    to_date(event_ts)                                   as event_date,
    date_trunc('hour', event_ts)                        as event_hour
  from source
  where viewer_id is not null
    and creator_id is not null
    and watch_ms >= 0
)

select *
from cleaned
