{{ config(materialized='table') }}

-- Billing source of truth: one row per customer per month.
-- billable_seats is multiplied by the per-seat rate on the invoice.
-- Metric contract: billable_seats is EXACT-REQUIRED (revenue / invoicing).

select
    s.customer_id,
    date_trunc('month', s.event_ts) as billing_month,
    count(distinct s.user_id) as billable_seats,
    sum(s.seat_rate) as gross_revenue
from {{ ref('fct_seat_activity') }} as s
group by
    s.customer_id,
    date_trunc('month', s.event_ts)
