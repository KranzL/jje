-- migrate:up
CREATE TABLE inventory_levels (
    id            BIGSERIAL PRIMARY KEY,
    product_id    BIGINT      NOT NULL REFERENCES products (id),
    warehouse_id  BIGINT      NOT NULL REFERENCES warehouses (id),
    on_hand_qty   INT         NOT NULL DEFAULT 0 CHECK (on_hand_qty >= 0),
    reserved_qty  INT         NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    reorder_point INT         NOT NULL DEFAULT 0 CHECK (reorder_point >= 0),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT inventory_levels_product_warehouse_key UNIQUE (product_id, warehouse_id),
    CONSTRAINT inventory_reserved_lte_on_hand CHECK (reserved_qty <= on_hand_qty)
);

CREATE INDEX inventory_levels_warehouse_idx ON inventory_levels (warehouse_id);

-- migrate:down
DROP TABLE inventory_levels;
