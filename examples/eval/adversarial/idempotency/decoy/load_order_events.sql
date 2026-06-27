CREATE TABLE IF NOT EXISTS mart.order_events (
    dedup_key      TEXT PRIMARY KEY,
    order_id       BIGINT       NOT NULL,
    event_type     TEXT         NOT NULL,
    amount_cents   BIGINT       NOT NULL,
    occurred_at    TIMESTAMPTZ  NOT NULL,
    loaded_at      TIMESTAMPTZ  NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.order_events_raw (
    order_id       BIGINT,
    event_type     TEXT,
    amount_cents   BIGINT,
    occurred_at    TIMESTAMPTZ,
    source_file    TEXT
);

WITH batch AS (
    SELECT CURRENT_TIMESTAMP AS run_ts
),
deduped AS (
    SELECT DISTINCT ON (o.order_id, o.event_type, o.occurred_at)
        o.order_id,
        o.event_type,
        o.amount_cents,
        o.occurred_at
    FROM staging.order_events_raw o
    WHERE o.order_id IS NOT NULL
      AND o.amount_cents >= 0
    ORDER BY o.order_id, o.event_type, o.occurred_at, o.source_file
),
prepared AS (
    SELECT
        d.order_id,
        d.event_type,
        d.amount_cents,
        d.occurred_at,
        b.run_ts AS loaded_at
    FROM deduped d
    CROSS JOIN batch b
)
INSERT INTO mart.order_events AS tgt (
    dedup_key,
    order_id,
    event_type,
    amount_cents,
    occurred_at,
    loaded_at
)
SELECT
    encode(
        digest(
            order_id::text    || '|' ||
            event_type        || '|' ||
            occurred_at::text,
            'sha256'
        ),
        'hex'
    ),
    order_id,
    event_type,
    amount_cents,
    occurred_at,
    loaded_at
FROM prepared
ON CONFLICT (dedup_key) DO UPDATE
    SET amount_cents = EXCLUDED.amount_cents,
        loaded_at    = EXCLUDED.loaded_at;
