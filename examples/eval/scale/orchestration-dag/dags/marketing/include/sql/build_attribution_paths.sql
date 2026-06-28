DELETE FROM {{ params.mart_schema }}.fct_attribution_paths
WHERE conversion_date = '{{ ds }}';

INSERT INTO {{ params.mart_schema }}.fct_attribution_paths
WITH conversions AS (
    SELECT
        c.conversion_id,
        c.user_id,
        c.converted_at,
        CAST(c.converted_at AS DATE) AS conversion_date,
        c.order_value_cents
    FROM raw.marketing_conversions c
    WHERE CAST(c.converted_at AS DATE) = '{{ ds }}'
),

path_touchpoints AS (
    SELECT
        cv.conversion_id,
        cv.user_id,
        cv.conversion_date,
        cv.order_value_cents,
        tp.touchpoint_id,
        tp.channel,
        tp.campaign_id,
        tp.occurred_at,
        ROW_NUMBER() OVER (
            PARTITION BY cv.conversion_id
            ORDER BY tp.occurred_at
        ) AS touch_position,
        COUNT(*) OVER (PARTITION BY cv.conversion_id) AS path_length
    FROM conversions cv
    JOIN {{ params.staging_schema }}.stg_touchpoints tp
        ON tp.user_id = cv.user_id
       AND tp.occurred_at <= cv.converted_at
       AND tp.occurred_at >= DATEADD(day, -{{ params.lookback_days }}, cv.converted_at)
)

SELECT
    conversion_id,
    user_id,
    conversion_date,
    touchpoint_id,
    channel,
    campaign_id,
    touch_position,
    path_length,
    order_value_cents,
    order_value_cents::FLOAT / NULLIF(path_length, 0) AS linear_credit_cents
FROM path_touchpoints;
