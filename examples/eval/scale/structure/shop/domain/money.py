from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CENTS = Decimal("0.01")


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal")
        if len(self.currency) != 3:
            raise ValueError("currency must be a 3-letter ISO code")

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(Decimal("0"), currency)

    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"currency mismatch: {self.currency} vs {other.currency}"
            )

    def add(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def scale(self, factor: Decimal) -> "Money":
        return Money(self.amount * factor, self.currency)

    def quantize(self) -> "Money":
        return Money(self.amount.quantize(CENTS, rounding=ROUND_HALF_UP), self.currency)

    def is_negative(self) -> bool:
        return self.amount < 0
