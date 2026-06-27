CREATE TABLE IF NOT EXISTS mart.payment_events (
    dedup_key      TEXT PRIMARY KEY,
    payment_id     BIGINT       NOT NULL,
    event_type     TEXT         NOT NULL,
    amount_cents   BIGINT       NOT NULL,
    occurred_at    TIMESTAMPTZ  NOT NULL,
    ingested_at    TIMESTAMPTZ  NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.payment_events_raw (
    payment_id     BIGINT,
    event_type     TEXT,
    amount_cents   BIGINT,
    occurred_at    TIMESTAMPTZ,
    source_file    TEXT
);

WITH batch AS (
    SELECT CURRENT_TIMESTAMP AS run_ts
),
deduped AS (
    SELECT DISTINCT ON (p.payment_id, p.event_type, p.occurred_at)
        p.payment_id,
        p.event_type,
        p.amount_cents,
        p.occurred_at
    FROM staging.payment_events_raw p
    WHERE p.payment_id IS NOT NULL
      AND p.amount_cents >= 0
    ORDER BY p.payment_id, p.event_type, p.occurred_at, p.source_file
),
prepared AS (
    SELECT
        d.payment_id,
        d.event_type,
        d.amount_cents,
        d.occurred_at,
        b.run_ts AS ingested_at
    FROM deduped d
    CROSS JOIN batch b
)
INSERT INTO mart.payment_events AS tgt (
    dedup_key,
    payment_id,
    event_type,
    amount_cents,
    occurred_at,
    ingested_at
)
SELECT
    encode(
        digest(
            payment_id::text || '|' ||
            event_type        || '|' ||
            occurred_at::text || '|' ||
            ingested_at::text,
            'sha256'
        ),
        'hex'
    ),
    payment_id,
    event_type,
    amount_cents,
    occurred_at,
    ingested_at
FROM prepared
ON CONFLICT (dedup_key) DO NOTHING;
