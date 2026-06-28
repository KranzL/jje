from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from shop.domain.money import Money


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

    def subtotal(self) -> Money:
        return self.unit_price.scale(Decimal(self.quantity))


@dataclass
class Order:
    order_id: str
    customer_id: str
    ship_to_region: str
    lines: List[LineItem] = field(default_factory=list)

    def add_line(self, item: LineItem) -> None:
        self.lines.append(item)

    def subtotal(self) -> Money:
        if not self.lines:
            return Money.zero()
        total = self.lines[0].subtotal()
        for line in self.lines[1:]:
            total = total.add(line.subtotal())
        return total

    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)
