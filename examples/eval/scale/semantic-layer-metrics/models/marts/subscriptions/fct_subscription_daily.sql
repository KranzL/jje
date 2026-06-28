{{
    config(
        materialized = 'table'
    )
}}

with subscriptions as (

    select * from {{ ref('stg_billing__subscriptions') }}

),

spine as (

    select cast(date_day as date) as snapshot_date
    from {{ ref('dim_date') }}
    where date_day between date('2023-01-01') and current_date()

),

active_days as (

    select
        s.subscription_id,
        s.account_id,
        s.plan_id,
        s.status,
        s.seat_count,
        s.mrr_amount,
        s.arr_amount,
        d.snapshot_date

    from subscriptions s
    inner join spine d
        on d.snapshot_date >= s.started_on
        and d.snapshot_date < coalesce(s.canceled_on, date('2999-12-31'))

)

select
    {{ dbt_utils.generate_surrogate_key(['subscription_id', 'snapshot_date']) }} as subscription_day_key,
    subscription_id,
    account_id,
    plan_id,
    status,
    snapshot_date,
    seat_count,
    mrr_amount,
    arr_amount

from active_days
