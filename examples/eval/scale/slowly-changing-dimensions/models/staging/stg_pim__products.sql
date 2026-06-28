with source as (

    select * from {{ source('pim', 'product_snapshots') }}

),

renamed as (

    select
        product_id,
        initcap(trim(product_name))       as product_name,
        upper(trim(category))             as category,
        cast(list_price as numeric(18,2)) as list_price,
        coalesce(is_discontinued, false)  as is_discontinued,
        snapshot_loaded_at                as record_loaded_at
    from source
    where product_id is not null

)

select * from renamed
