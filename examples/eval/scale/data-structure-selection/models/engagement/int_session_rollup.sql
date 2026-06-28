{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['event_date'],
    file_format='delta'
  )
}}

with events as (
  select
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
    event_hour,
    event_date
  from {{ ref('stg_playback_events') }}

  {% if is_incremental() %}
  where event_date >= date_sub(current_date(), 2)
  {% endif %}
),

session_grain as (
  select
    creator_id,
    viewer_id,
    session_id,
    event_date,
    min(event_hour)                                     as session_start_hour,
    count(distinct video_id)                            as videos_watched,
    count(distinct device_type)                         as devices_used,
    max(country_code)                                   as country_code,
    sum(watch_ms)                                       as total_watch_ms,
    sum(buffer_ms)                                      as total_buffer_ms,
    avg(bitrate_kbps)                                   as avg_bitrate_kbps,
    sum(case when event_type = 'complete' then 1 else 0 end) as completions
  from events
  group by creator_id, viewer_id, session_id, event_date
)

select
  creator_id,
  viewer_id,
  session_id,
  event_date,
  session_start_hour,
  videos_watched,
  devices_used,
  country_code,
  total_watch_ms,
  total_buffer_ms,
  avg_bitrate_kbps,
  completions,
  round(total_buffer_ms / nullif(total_watch_ms + total_buffer_ms, 0), 4) as rebuffer_ratio
from session_grain
