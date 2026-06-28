{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['payout_date'],
    file_format='delta',
    tags=['finance', 'nightly']
  )
}}

with sessions as (
  select
    creator_id,
    viewer_id,
    session_id,
    event_date,
    total_watch_ms,
    completions
  from {{ ref('int_session_rollup') }}

  {% if is_incremental() %}
  where event_date = date_sub(current_date(), 1)
  {% endif %}
),

monetizable as (
  select
    creator_id,
    event_date                                           as payout_date,
    count(distinct session_id)                           as billable_sessions,
    count(distinct viewer_id)                            as billable_viewers,
    sum(total_watch_ms) / 3600000.0                      as billable_watch_hours,
    sum(completions)                                     as billable_completions
  from sessions
  where total_watch_ms >= 30000
  group by creator_id, event_date
)

select
  creator_id,
  payout_date,
  billable_sessions,
  billable_viewers,
  billable_watch_hours,
  billable_completions,
  round(billable_watch_hours * {{ var('payout_rate_per_hour', 0.012) }}, 4) as estimated_payout_usd
from monetizable
