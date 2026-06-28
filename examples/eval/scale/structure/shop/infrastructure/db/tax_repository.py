from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from shop.infrastructure.db.connection import Connection, get_default_connection


_SEED_RATES: Dict[str, str] = {
    "US-CA": "0.0725",
    "US-NY": "0.04",
    "US-TX": "0.0625",
    "US-OR": "0.0",
}


class SqlTaxRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    @classmethod
    def default_connection(cls) -> "SqlTaxRepository":
        return cls(get_default_connection())

    def rate_for_region(self, region: str) -> Optional[Decimal]:
        row = self._connection.fetch_one(
            "SELECT rate FROM tax_rates WHERE region = ?", (region,)
        )
        if row is not None:
            return Decimal(str(row["rate"]))
        seed = _SEED_RATES.get(region)
        return Decimal(seed) if seed is not None else None

    def upsert_rate(self, region: str, rate: Decimal) -> None:
        self._connection.execute(
            "INSERT INTO tax_rates(region, rate) VALUES(?, ?) "
            "ON CONFLICT(region) DO UPDATE SET rate = excluded.rate",
            (region, str(rate)),
        )
