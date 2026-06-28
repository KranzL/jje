from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shop.domain.order import Order
from shop.domain.pricing import PricedOrder, PricingService
from shop.infrastructure.adapters import FlatPromotionAdapter, TaxRateAdapter
from shop.infrastructure.db.tax_repository import SqlTaxRepository


@dataclass
class CheckoutResult:
    order_id: str
    priced: PricedOrder


def build_pricing_service(loyalty_percent: Decimal = Decimal("0.05")) -> PricingService:
    tax_repo = SqlTaxRepository.default_connection()
    tax_rates = TaxRateAdapter(tax_repo)
    promotions = FlatPromotionAdapter(loyalty_percent)
    return PricingService(tax_rates=tax_rates, promotions=promotions)


class CheckoutService:
    def __init__(self, pricing: PricingService) -> None:
        self._pricing = pricing

    def checkout(self, order: Order) -> CheckoutResult:
        priced = self._pricing.price(order)
        if priced.total.is_negative():
            raise ValueError("order total cannot be negative")
        return CheckoutResult(order_id=order.order_id, priced=priced)
