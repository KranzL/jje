{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['payment_id', 'event_type'],
        on_schema_change='append_new_columns'
    )
}}

with events as (

    select * from {{ ref('fct_payment_events') }}

    {% if is_incremental() %}
    where ingested_at > (select max(latest_ingested_at) from {{ this }})
    {% endif %}

),

pivoted as (

    select
        payment_id,
        event_type,
        count(*)                                        as event_count,
        min(occurred_at)                                as first_seen_at,
        max(occurred_at)                                as last_seen_at,
        max(ingested_at)                                as latest_ingested_at
    from events
    group by 1, 2

)

select * from pivoted
