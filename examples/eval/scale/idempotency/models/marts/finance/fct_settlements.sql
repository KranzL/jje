{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='settlement_id',
        on_schema_change='sync_all_columns'
    )
}}

with settlements as (

    select * from {{ ref('stg_settlement_batches') }}

    {% if is_incremental() %}
    where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}

),

final as (

    select
        settlement_id,
        settled_on,
        gross_minor,
        fee_minor,
        net_minor,
        currency_code,
        ingested_at
    from settlements

)

select * from final
