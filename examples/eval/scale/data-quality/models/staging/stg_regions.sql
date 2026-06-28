with source as (

    select * from {{ source('shop', 'region_history') }}

),

renamed as (

    select
        region_id,
        region_name,
        sales_territory,
        is_current,
        valid_from,
        valid_to

    from source

),

current_only as (

    select
        region_id,
        region_name,
        sales_territory

    from renamed

    where is_current = true

)

select * from current_only
