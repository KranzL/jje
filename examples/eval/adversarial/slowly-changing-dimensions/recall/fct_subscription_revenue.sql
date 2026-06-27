{{
    config(
        materialized='incremental',
        unique_key='subscription_event_key',
        incremental_strategy='merge'
    )
}}

with billing_events as (

    select
        be.billing_event_id,
        be.subscription_id,
        be.account_id,
        be.plan_code,
        be.amount_billed,
        be.currency_code,
        be.charged_at
    from {{ ref('stg_billing__events') }} be

    {% if is_incremental() %}
    where be.charged_at > (select max(charged_at) from {{ this }})
    {% endif %}

),

plan_versions as (

    select
        plan_code,
        plan_tier,
        list_price_monthly,
        discount_pct,
        effective_at
    from {{ ref('stg_billing__plan_catalog') }}

),

plan_history as (

    select
        plan_code,
        plan_tier,
        list_price_monthly,
        discount_pct,
        effective_at as valid_from,
        coalesce(
            lead(effective_at) over (
                partition by plan_code
                order by effective_at
            ),
            cast('2999-12-31' as timestamp)
        ) as valid_to
    from plan_versions

),

accounts as (

    select
        account_id,
        account_segment,
        billing_country_code
    from {{ ref('dim_account') }}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['be.billing_event_id']) }} as subscription_event_key,

        be.subscription_id,
        be.account_id as account_key,
        a.account_segment,
        a.billing_country_code,

        be.plan_code,
        ph.plan_tier,
        ph.list_price_monthly,
        ph.discount_pct,

        be.currency_code,
        be.amount_billed,
        round(ph.list_price_monthly * (1 - ph.discount_pct), 2) as expected_amount,

        be.charged_at
    from billing_events be
    inner join accounts a
        on be.account_id = a.account_id
    inner join plan_history ph
        on be.plan_code = ph.plan_code
        and be.charged_at between ph.valid_from and ph.valid_to

)

select * from final
