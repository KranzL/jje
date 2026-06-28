from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol

from shop.domain.money import Money
from shop.domain.order import Order


class OrderRepository(Protocol):
    def get(self, order_id: str) -> Optional[Order]:
        ...

    def save(self, order: Order) -> None:
        ...


class TaxRateProvider(Protocol):
    def rate_for_region(self, region: str) -> Decimal:
        ...


class PromotionProvider(Protocol):
    def discount_for(self, customer_id: str, subtotal: Money) -> Money:
        ...
