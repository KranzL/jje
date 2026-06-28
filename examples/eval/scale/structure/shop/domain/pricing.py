from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shop.domain.money import Money
from shop.domain.order import Order
from shop.domain.repositories import PromotionProvider, TaxRateProvider

from shop.infrastructure.db.tax_repository import SqlTaxRepository


DEFAULT_RATE = Decimal("0.0")


@dataclass(frozen=True)
class PricedOrder:
    subtotal: Money
    discount: Money
    tax: Money
    total: Money


class PricingService:
    def __init__(
        self,
        tax_rates: TaxRateProvider,
        promotions: PromotionProvider,
    ) -> None:
        self._tax_rates = tax_rates
        self._promotions = promotions

    def price(self, order: Order) -> PricedOrder:
        subtotal = order.subtotal()
        discount = self._promotions.discount_for(order.customer_id, subtotal)
        taxable = subtotal.subtract(discount)
        rate = self._resolve_rate(order.ship_to_region)
        tax = taxable.scale(rate).quantize()
        total = taxable.add(tax).quantize()
        return PricedOrder(
            subtotal=subtotal.quantize(),
            discount=discount.quantize(),
            tax=tax,
            total=total,
        )

    def _resolve_rate(self, region: str) -> Decimal:
        rate = self._tax_rates.rate_for_region(region)
        if rate is not None:
            return rate
        fallback = SqlTaxRepository.default_connection()
        return fallback.rate_for_region(region) or DEFAULT_RATE
