from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Dict, Optional

from .invoice import Invoice

RateLookup = Callable[[str], Decimal]


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ChargeCalculator:
    def __init__(self, rate_lookup: Optional[RateLookup] = None) -> None:
        self._rate_lookup = rate_lookup
        self._discount_tiers: Dict[Decimal, Decimal] = {
            Decimal("1000"): Decimal("0.05"),
            Decimal("5000"): Decimal("0.10"),
        }

    def _discount_rate(self, subtotal: Decimal) -> Decimal:
        applicable = Decimal("0")
        for threshold, rate in sorted(self._discount_tiers.items()):
            if subtotal >= threshold:
                applicable = rate
        return applicable

    def discounted_subtotal(self, invoice: Invoice) -> Decimal:
        subtotal = invoice.subtotal()
        rate = self._discount_rate(subtotal)
        return _round_money(subtotal * (Decimal("1") - rate))

    def tax_for(self, invoice: Invoice, region: str) -> Decimal:
        if self._rate_lookup is not None:
            rate = self._rate_lookup(region)
        else:
            from ..infra.rates import resolve_region_rate

            rate = resolve_region_rate(region, invoice.currency)
        taxable = self.discounted_subtotal(invoice)
        return _round_money(taxable * rate)

    def total(self, invoice: Invoice, region: str) -> Decimal:
        return self.discounted_subtotal(invoice) + self.tax_for(invoice, region)
