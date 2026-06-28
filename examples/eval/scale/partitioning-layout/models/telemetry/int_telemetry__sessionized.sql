{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by=['event_date'],
    file_format='delta',
    cluster_by=['device_id', 'session_id']
  )
}}

with events as (
  select
    event_id,
    device_id,
    session_id,
    event_name,
    event_ts,
    ingested_at,
    to_date(event_ts)                                    as event_date,
    dt
  from {{ ref('stg_telemetry__events') }}

  {% if is_incremental() %}
  where dt >= date_format(date_sub(current_date(), 3), 'yyyy-MM-dd')
  {% endif %}
),

ordered as (
  select
    *,
    row_number() over (
      partition by session_id
      order by event_ts
    )                                                    as event_seq,
    min(event_ts) over (partition by session_id)         as session_start_ts,
    max(event_ts) over (partition by session_id)         as session_end_ts
  from events
)

select
  event_id,
  device_id,
  session_id,
  event_name,
  event_ts,
  ingested_at,
  event_seq,
  session_start_ts,
  session_end_ts,
  event_date
from ordered
