{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='payment_id',
        on_schema_change='append_new_columns',
        cluster_by=['event_date']
    )
}}

with events as (

    select * from {{ ref('stg_payment_events') }}

    {% if is_incremental() %}
    where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}

),

dim_payment as (

    select
        payment_id,
        order_id,
        customer_sk
    from {{ ref('dim_payment') }}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['e.payment_id', 'e.event_type']) }}
                                                        as payment_event_sk,
        e.event_id,
        e.payment_id,
        e.order_id,
        d.customer_sk,
        e.event_type,
        e.amount_minor,
        e.currency_code,
        e.occurred_at,
        cast(e.occurred_at as date)                     as event_date,
        e.ingested_at
    from events e
    left join dim_payment d
        on e.payment_id = d.payment_id

)

select * from final
