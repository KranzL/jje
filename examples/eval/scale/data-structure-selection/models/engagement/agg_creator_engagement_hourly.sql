{{
  config(
    materialized='view',
    tags=['dashboard', 'creator_facing']
  )
}}

with sessions as (
  select
    creator_id,
    viewer_id,
    session_start_hour,
    event_date,
    total_watch_ms,
    videos_watched,
    completions,
    rebuffer_ratio,
    country_code
  from {{ ref('int_session_rollup') }}
  where event_date >= date_sub(current_date(), 7)
),

hourly as (
  select
    creator_id,
    session_start_hour,
    to_date(session_start_hour)                          as engagement_date,
    count(distinct viewer_id)                            as unique_viewers,
    count(distinct country_code)                         as countries_reached,
    sum(videos_watched)                                  as videos_watched,
    sum(completions)                                     as completions,
    sum(total_watch_ms) / 3600000.0                      as total_watch_hours,
    percentile(total_watch_ms, 0.5)                      as median_session_ms,
    percentile(total_watch_ms, 0.95)                     as p95_session_ms,
    avg(rebuffer_ratio)                                  as avg_rebuffer_ratio
  from sessions
  group by creator_id, session_start_hour
)

select
  creator_id,
  session_start_hour,
  engagement_date,
  unique_viewers,
  countries_reached,
  videos_watched,
  completions,
  round(total_watch_hours, 2)                            as total_watch_hours,
  median_session_ms,
  p95_session_ms,
  round(completions / nullif(videos_watched, 0), 4)      as completion_rate,
  round(avg_rebuffer_ratio, 4)                           as avg_rebuffer_ratio
from hourly
