-- migrate:up
CREATE TYPE stock_movement_kind AS ENUM ('receipt', 'shipment', 'adjustment', 'transfer');

CREATE TABLE stock_movements (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT      NOT NULL REFERENCES products (id),
    warehouse_id    BIGINT      NOT NULL REFERENCES warehouses (id),
    kind            stock_movement_kind NOT NULL,
    quantity_delta  INT         NOT NULL,
    unit_cost       NUMERIC(12,2) NOT NULL CHECK (unit_cost >= 0),
    extended_cost   NUMERIC(14,2) NOT NULL CHECK (extended_cost >= 0),
    reference_code  TEXT        NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT stock_movements_reference_code_key UNIQUE (reference_code)
);

CREATE INDEX stock_movements_product_idx ON stock_movements (product_id, occurred_at);
CREATE INDEX stock_movements_warehouse_idx ON stock_movements (warehouse_id, occurred_at);

-- migrate:down
DROP TABLE stock_movements;
DROP TYPE stock_movement_kind;
