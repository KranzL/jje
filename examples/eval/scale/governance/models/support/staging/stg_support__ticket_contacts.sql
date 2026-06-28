with source as (

    select * from {{ source('zendesk', 'ticket_contacts') }}

),

renamed as (

    select
        id                              as contact_id,
        ticket_id,
        role                            as contact_role,
        lower(email)                    as requester_email,
        phone                           as requester_phone,
        backup_email                    as ext_ref,
        country_code,
        cast(is_verified as boolean)    as is_verified,
        created_at

    from source

),

final as (

    select
        contact_id,
        ticket_id,
        contact_role,
        requester_email,
        requester_phone,
        ext_ref,
        country_code,
        is_verified,
        created_at
    from renamed
    where contact_role in ('requester', 'cc')

)

select * from final
