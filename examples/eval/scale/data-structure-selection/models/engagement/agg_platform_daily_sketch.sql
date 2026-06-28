{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['engagement_date'],
    file_format='delta',
    tags=['internal', 'trend']
  )
}}

with sessions as (
  select
    viewer_id,
    event_date,
    total_watch_ms,
    completions,
    rebuffer_ratio
  from {{ ref('int_session_rollup') }}

  {% if is_incremental() %}
  where event_date >= date_sub(current_date(), 3)
  {% endif %}
),

daily as (
  select
    event_date                                           as engagement_date,
    approx_count_distinct(viewer_id)                     as approx_unique_viewers,
    percentile_approx(total_watch_ms, 0.5, 1000)         as median_session_ms,
    percentile_approx(total_watch_ms, 0.95, 1000)        as p95_session_ms,
    sum(completions)                                     as completions,
    avg(rebuffer_ratio)                                  as avg_rebuffer_ratio
  from sessions
  group by event_date
)

select
  engagement_date,
  approx_unique_viewers,
  median_session_ms,
  p95_session_ms,
  completions,
  round(avg_rebuffer_ratio, 4)                           as avg_rebuffer_ratio
from daily
