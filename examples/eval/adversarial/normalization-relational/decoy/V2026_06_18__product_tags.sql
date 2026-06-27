SET search_path TO catalog, public;

CREATE TABLE catalog.product_tags (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id   BIGINT      NOT NULL REFERENCES catalog.products (id) ON DELETE CASCADE,
    tag_id       BIGINT      NOT NULL REFERENCES catalog.tags (id) ON DELETE CASCADE,
    sort_order   INTEGER     NOT NULL DEFAULT 0,
    applied_by   BIGINT      REFERENCES identity.users (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_product_tags_tag
    ON catalog.product_tags (tag_id);

CREATE UNIQUE INDEX uq_product_tags_pair
    ON catalog.product_tags (product_id, tag_id);

COMMENT ON TABLE catalog.product_tags IS
    'Junction of products to tags; surrogate id lets the pivot row be referenced by audit events.';
