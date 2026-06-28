with events as (

    select * from {{ source('zendesk', 'ticket_events') }}

),

tickets as (

    select * from {{ ref('stg_support__tickets') }}

),

joined as (

    select
        e.id                       as ticket_event_id,
        e.ticket_id,
        t.external_ticket_ref,
        t.agent_identifier,
        t.contact_channel,
        t.ticket_priority,
        e.field_name               as changed_field,
        e.previous_value,
        e.new_value,
        e.actor_id,
        e.occurred_at,
        cast(e.occurred_at as date) as event_date

    from events e
    inner join tickets t
        on e.ticket_id = t.ticket_id

),

final as (

    select
        ticket_event_id,
        ticket_id,
        external_ticket_ref,
        agent_identifier,
        contact_channel,
        ticket_priority,
        changed_field,
        previous_value,
        new_value,
        actor_id,
        occurred_at,
        event_date
    from joined
    where changed_field in ('status', 'priority', 'assignee', 'group')

)

select * from final
