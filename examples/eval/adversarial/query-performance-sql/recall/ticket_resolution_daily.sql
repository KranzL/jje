CREATE TABLE IF NOT EXISTS ops.support_tickets (
  ticket_id    bigint      PRIMARY KEY,
  account_id   bigint      NOT NULL,
  assignee_id  bigint,
  queue        text        NOT NULL,
  priority     smallint    NOT NULL,
  status       text        NOT NULL,
  created_at   timestamptz NOT NULL,
  resolved_at  timestamptz
);

CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON ops.support_tickets (created_at);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee   ON ops.support_tickets (assignee_id);

CREATE TABLE IF NOT EXISTS ops.agents (
  agent_id  bigint PRIMARY KEY,
  team      text   NOT NULL,
  region    text   NOT NULL
);

WITH day_bounds AS (
  SELECT
    timestamp '2026-06-01 00:00:00' AS lo,
    timestamp '2026-06-02 00:00:00' AS hi
),
in_window AS (
  SELECT
    t.ticket_id,
    t.assignee_id,
    t.queue,
    t.priority,
    t.status,
    t.created_at,
    t.resolved_at
  FROM ops.support_tickets t
  CROSS JOIN day_bounds b
  WHERE (t.created_at AT TIME ZONE 'America/New_York') >= b.lo
    AND (t.created_at AT TIME ZONE 'America/New_York') <  b.hi
    AND t.status <> 'spam'
)
SELECT
  a.team,
  a.region,
  w.queue,
  w.priority,
  count(*)                                               AS tickets,
  count(*) FILTER (WHERE w.resolved_at IS NOT NULL)      AS resolved,
  avg(extract(epoch FROM (w.resolved_at - w.created_at))) AS avg_resolve_secs
FROM in_window w
JOIN ops.agents a ON a.agent_id = w.assignee_id
GROUP BY a.team, a.region, w.queue, w.priority
ORDER BY tickets DESC;
