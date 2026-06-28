with source as (

    select * from {{ source('crm', 'customer_snapshots') }}

),

renamed as (

    select
        customer_id,
        lower(trim(email))                as email,
        initcap(trim(full_name))          as full_name,
        upper(trim(country_code))         as country_code,
        nullif(trim(account_tier), '')    as account_tier,
        sales_region_id,
        is_active,
        snapshot_loaded_at                as record_loaded_at
    from source
    where customer_id is not null

),

deduped as (

    select
        *,
        row_number() over (
            partition by customer_id, record_loaded_at
            order by record_loaded_at desc
        ) as rn
    from renamed

)

select
    * exclude (rn)
from deduped
where rn = 1
