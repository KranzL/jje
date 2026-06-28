with contacts as (

    select * from {{ ref('stg_support__ticket_contacts') }}
    where contact_role = 'requester'

),

ranked as (

    select
        *,
        row_number() over (
            partition by ticket_id
            order by created_at desc
        ) as rn
    from contacts

),

requesters as (

    select
        contact_id             as requester_key,
        ticket_id,
        requester_email,
        requester_phone,
        ext_ref,
        country_code,
        is_verified,
        created_at
    from ranked
    where rn = 1

)

select * from requesters
