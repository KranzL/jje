# Inventory catalog schema

Adds the warehouse + product catalog domain used by the fulfillment service.

## Tables

- `warehouses` - physical stocking locations, keyed by `code`.
- `product_categories` - self-referencing category tree, keyed by `slug`.
- `products` - sellable items, identified by `sku`.
- `inventory_levels` - one row per (product, warehouse) with on-hand and reserved counts.
- `stock_movements` - append-only ledger of receipts, shipments, adjustments, and transfers.
  Each row captures `unit_cost` and `extended_cost` at the time of the movement so the ledger
  stays correct even after a product's list price changes later.

## Migrations

Run with `dbmate up`. Migrations 0042-0046 are additive and safe to apply online.

## Access layer

`repository.py` exposes upsert and lookup helpers. Product ingestion from the supplier feed
upserts by `sku`; inventory sync upserts by `(product_id, warehouse_id)`.
