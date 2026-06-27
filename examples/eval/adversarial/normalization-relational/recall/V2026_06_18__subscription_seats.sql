SET search_path TO billing, public;

CREATE TABLE billing.subscription_seats (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id      BIGINT      NOT NULL REFERENCES billing.accounts (id),
    member_id       BIGINT      NOT NULL REFERENCES identity.members (id),
    plan_tier       TEXT        NOT NULL DEFAULT 'standard',
    seat_label      TEXT,
    billable        BOOLEAN     NOT NULL DEFAULT TRUE,
    activated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deactivated_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_seat_window CHECK (deactivated_at IS NULL OR deactivated_at >= activated_at)
);

CREATE INDEX idx_subscription_seats_account
    ON billing.subscription_seats (account_id);

CREATE INDEX idx_subscription_seats_member
    ON billing.subscription_seats (account_id, member_id);

CREATE INDEX idx_subscription_seats_billable
    ON billing.subscription_seats (account_id)
    WHERE billable AND deactivated_at IS NULL;

COMMENT ON TABLE billing.subscription_seats IS
    'One row per member granted a seat under an account subscription.';
