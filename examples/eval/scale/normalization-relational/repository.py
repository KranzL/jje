from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import InventoryLevel, Product, Warehouse


def get_product_by_sku(session: Session, sku: str) -> Product | None:
    return session.scalar(select(Product).where(Product.sku == sku))


def upsert_product(session: Session, payload: dict) -> None:
    stmt = insert(Product).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Product.sku],
        set_={
            "name": stmt.excluded.name,
            "list_price": stmt.excluded.list_price,
            "weight_grams": stmt.excluded.weight_grams,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)


def upsert_inventory_level(session: Session, payload: dict) -> None:
    stmt = insert(InventoryLevel).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=[InventoryLevel.product_id, InventoryLevel.warehouse_id],
        set_={
            "on_hand_qty": stmt.excluded.on_hand_qty,
            "reserved_qty": stmt.excluded.reserved_qty,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)


def get_warehouse_by_code(session: Session, code: str) -> Warehouse | None:
    return session.scalar(select(Warehouse).where(Warehouse.code == code))


def list_low_stock(session: Session, warehouse_id: int) -> list[InventoryLevel]:
    stmt = (
        select(InventoryLevel)
        .where(InventoryLevel.warehouse_id == warehouse_id)
        .where(InventoryLevel.on_hand_qty <= InventoryLevel.reorder_point)
    )
    return list(session.scalars(stmt))
