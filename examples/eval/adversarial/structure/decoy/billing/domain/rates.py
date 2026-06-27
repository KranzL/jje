from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class RateRepository(Protocol):
    def rate_for(self, region: str, currency: str) -> Decimal:
        ...
