-- migrate:up
CREATE TABLE products (
    id            BIGSERIAL PRIMARY KEY,
    sku           TEXT        NOT NULL,
    category_id   BIGINT      NOT NULL REFERENCES product_categories (id),
    name          TEXT        NOT NULL,
    description   TEXT,
    list_price    NUMERIC(12,2) NOT NULL CHECK (list_price >= 0),
    weight_grams  INT         NOT NULL CHECK (weight_grams >= 0),
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX products_sku_idx ON products (sku);
CREATE INDEX products_category_idx ON products (category_id);

-- migrate:down
DROP TABLE products;
