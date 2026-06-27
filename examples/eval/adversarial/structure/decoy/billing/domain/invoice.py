from dataclasses import dataclass, field
from decimal import Decimal
from typing import List


@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int
    unit_price: Decimal

    def extended(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Invoice:
    customer_id: str
    currency: str
    lines: List[LineItem] = field(default_factory=list)

    def subtotal(self) -> Decimal:
        return sum((line.extended() for line in self.lines), Decimal("0"))

    def add(self, item: LineItem) -> None:
        if item.quantity <= 0:
            raise ValueError("quantity must be positive")
        self.lines.append(item)
