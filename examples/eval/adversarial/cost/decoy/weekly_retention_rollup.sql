INSERT OVERWRITE TABLE analytics.weekly_retention_rollup PARTITION (dt)
WITH bounds AS (
  SELECT
    date_format(date_sub(current_date(), 28), 'yyyy-MM-dd') AS window_start,
    date_format(date_sub(current_date(), 1),  'yyyy-MM-dd') AS window_end
),
sessions AS (
  SELECT
    e.account_id,
    e.dt,
    e.platform,
    e.session_id,
    cast(date_trunc('week', cast(e.event_ts AS timestamp)) AS date) AS week_start,
    coalesce(e.duration_ms, 0)                                      AS duration_ms,
    cast(e.event_payload['is_active'] AS int)                       AS active_flag
  FROM warehouse.fct_app_events e
  CROSS JOIN bounds b
  WHERE e.dt BETWEEN b.window_start AND b.window_end
    AND e.event_name = 'engagement'
    AND e.platform IN ('ios', 'android', 'web')
),
graded AS (
  SELECT
    account_id,
    dt,
    platform,
    week_start,
    session_id,
    sum(duration_ms) / 1000.0 AS session_seconds,
    max(active_flag)          AS was_active
  FROM sessions
  GROUP BY account_id, dt, platform, week_start, session_id
)
SELECT
  account_id,
  platform,
  week_start,
  count(DISTINCT session_id)                       AS sessions,
  round(sum(session_seconds), 2)                   AS total_seconds,
  sum(CASE WHEN was_active = 1 THEN 1 ELSE 0 END)  AS active_sessions,
  dt
FROM graded
GROUP BY account_id, platform, week_start, dt
