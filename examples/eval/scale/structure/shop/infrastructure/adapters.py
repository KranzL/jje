from __future__ import annotations

from decimal import Decimal

from shop.domain.money import Money
from shop.infrastructure.db.tax_repository import SqlTaxRepository


class TaxRateAdapter:
    def __init__(self, repository: SqlTaxRepository) -> None:
        self._repository = repository

    def rate_for_region(self, region: str) -> Decimal:
        rate = self._repository.rate_for_region(region)
        return rate if rate is not None else Decimal("0.0")


class FlatPromotionAdapter:
    def __init__(self, percent_off: Decimal) -> None:
        self._percent_off = percent_off

    def discount_for(self, customer_id: str, subtotal: Money) -> Money:
        if not customer_id:
            return Money.zero(subtotal.currency)
        return subtotal.scale(self._percent_off).quantize()
