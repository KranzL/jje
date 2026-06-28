{{
    config(
        materialized='table',
        unique_key='product_history_key'
    )
}}

with staged as (

    select * from {{ ref('stg_pim__products') }}

),

change_detection as (

    select
        *,
        {{ dbt_utils.generate_surrogate_key([
            'product_name',
            'category',
            'list_price',
            'is_discontinued'
        ]) }} as attribute_hash,
        lag({{ dbt_utils.generate_surrogate_key([
            'product_name',
            'category',
            'list_price',
            'is_discontinued'
        ]) }}) over (
            partition by product_id
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
        product_id,
        product_name,
        category,
        list_price,
        is_discontinued,
        record_loaded_at as valid_from,
        lead(record_loaded_at) over (
            partition by product_id
            order by record_loaded_at
        ) as valid_to
    from changed_only

)

select
    {{ dbt_utils.generate_surrogate_key(['product_id', 'valid_from']) }} as product_history_key,
    product_id,
    product_name,
    category,
    list_price,
    is_discontinued,
    valid_from,
    coalesce(valid_to, cast('9999-12-31 23:59:59' as timestamp)) as valid_to,
    valid_to is null as is_current
from versioned
