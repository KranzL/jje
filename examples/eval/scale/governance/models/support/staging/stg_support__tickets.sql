with source as (

    select * from {{ source('zendesk', 'tickets') }}

),

renamed as (

    select
        id                              as ticket_id,
        external_id                     as external_ticket_ref,
        requester_id,
        assignee_id                     as agent_identifier,
        organization_id,
        group_id,
        lower(channel)                  as contact_channel,
        status                          as ticket_status,
        priority                        as ticket_priority,
        subject                         as ticket_subject,
        satisfaction_rating,
        created_at,
        updated_at,
        cast(created_at as date)        as created_date

    from source

    where status not in ('deleted')

)

select * from renamed
