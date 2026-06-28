-- migrate:up
CREATE TABLE product_categories (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    parent_id   BIGINT      REFERENCES product_categories (id),
    sort_order  INT         NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT product_categories_slug_key UNIQUE (slug)
);

CREATE INDEX product_categories_parent_idx ON product_categories (parent_id);

-- migrate:down
DROP TABLE product_categories;
