{{
  config(
    materialized='table',
    file_format='delta'
  )
}}

select
  device_id,
  account_id,
  platform
from {{ source('raw', 'device_registry') }}
where device_id is not null
