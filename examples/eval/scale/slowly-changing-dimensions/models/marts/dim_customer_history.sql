{{
    config(
        materialized='table',
        unique_key='customer_history_key'
    )
}}

with staged as (

    select * from {{ ref('stg_crm__customers') }}

),

change_detection as (

    select
        *,
        {{ dbt_utils.generate_surrogate_key([
            'email',
            'full_name',
            'country_code',
            'account_tier',
            'sales_region_id',
            'is_active'
        ]) }} as attribute_hash,
        lag({{ dbt_utils.generate_surrogate_key([
            'email',
            'full_name',
            'country_code',
            'account_tier',
            'sales_region_id',
            'is_active'
        ]) }}) over (
            partition by customer_id
            order by record_loaded_at
        ) as prev_attribute_hash
    from staged

),

changed_only as (

    select *
    from change_detection
    where prev_attribute_hash is null
       or attribute_hash != prev_attribute_hash

),

versioned as (

    select
        customer_id,
        email,
        full_name,
        country_code,
        account_tier,
        sales_region_id,
        is_active,
        record_loaded_at as valid_from,
        lead(record_loaded_at) over (
            partition by customer_id
            order by record_loaded_at
        ) as valid_to
    from changed_only

)

select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'valid_from']) }} as customer_history_key,
    customer_id,
    email,
    full_name,
    country_code,
    account_tier,
    sales_region_id,
    is_active,
    valid_from,
    coalesce(valid_to, cast('9999-12-31 23:59:59' as timestamp)) as valid_to,
    valid_to is null as is_current
from versioned
