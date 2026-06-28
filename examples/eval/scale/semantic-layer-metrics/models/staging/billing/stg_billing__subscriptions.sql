with source as (

    select * from {{ source('billing', 'subscriptions') }}

),

renamed as (

    select
        subscription_id,
        account_id,
        plan_id,
        cast(seats as integer)                  as seat_count,
        cast(mrr_cents as numeric) / 100.0      as mrr_amount,
        cast(arr_cents as numeric) / 100.0      as arr_amount,
        status,
        cast(started_at as date)                as started_on,
        cast(canceled_at as date)               as canceled_on,
        cast(updated_at as timestamp)           as updated_at

    from source

)

select * from renamed
