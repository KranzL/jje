with source as (

    select * from {{ source('crm', 'order_rep_assignments') }}

),

renamed as (

    select
        id                          as assignment_id,
        order_id,
        sales_rep_id,
        rep_name,
        credit_share,
        assigned_at

    from source

    where is_void = false

)

select * from renamed
