-- migrate:up
CREATE TABLE warehouses (
    id          BIGSERIAL PRIMARY KEY,
    code        TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    region      TEXT        NOT NULL,
    address_1   TEXT        NOT NULL,
    address_2   TEXT,
    city        TEXT        NOT NULL,
    postal_code TEXT        NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT warehouses_code_key UNIQUE (code)
);

CREATE INDEX warehouses_region_idx ON warehouses (region);

-- migrate:down
DROP TABLE warehouses;
