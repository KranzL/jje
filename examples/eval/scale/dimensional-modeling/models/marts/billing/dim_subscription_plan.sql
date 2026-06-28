{{
    config(
        materialized = 'table'
    )
}}

with plan_versions as (

    select * from {{ ref('stg_billing__plan_versions') }}

),

scd2 as (

    select
        {{ dbt_utils.generate_surrogate_key(['plan_id', 'valid_from']) }} as plan_version_key,
        plan_id,
        plan_name,
        plan_family,
        billing_interval,
        list_price_monthly,
        seat_based_flag,
        valid_from,
        coalesce(
            lead(valid_from) over (
                partition by plan_id
                order by valid_from
            ),
            timestamp('2999-12-31')
        )                                                               as valid_to,
        row_number() over (
            partition by plan_id
            order by valid_from desc
        ) = 1                                                           as is_current

    from plan_versions

)

select
    plan_version_key,
    plan_id,
    plan_name,
    plan_family,
    billing_interval,
    list_price_monthly,
    seat_based_flag,
    valid_from,
    valid_to,
    is_current

from scd2
