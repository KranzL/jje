DELETE FROM {{ params.staging_schema }}.stg_touchpoints
WHERE event_date = '{{ ds }}';

INSERT INTO {{ params.staging_schema }}.stg_touchpoints
SELECT
    t.touchpoint_id,
    t.anonymous_id,
    t.user_id,
    t.channel,
    t.campaign_id,
    t.occurred_at,
    CAST(t.occurred_at AS DATE)        AS event_date,
    t.utm_source,
    t.utm_medium,
    t.utm_campaign,
    t.revenue_cents
FROM raw.marketing_touchpoints t
WHERE CAST(t.occurred_at AS DATE) = '{{ ds }}'
  AND t.channel IN ({{ params.channel_list }});
