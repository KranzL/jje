{{
  config(
    materialized = 'table',
    partition_by = {'field': 'event_date', 'data_type': 'date'}
  )
}}

select
  user_id,
  event_date,
  count(*) as event_count
from {{ source('analytics', 'events') }}
group by user_id, event_date
