with source as (

    select * from {{ source('billing', 'plan_versions') }}

),

renamed as (

    select
        plan_id,
        plan_name,
        plan_family,
        billing_interval,
        list_price_monthly,
        is_seat_based                   as seat_based_flag,
        effective_from::timestamp       as valid_from

    from source

)

select * from renamed
