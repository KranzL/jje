import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator

from ..domain.rates import RateRepository


class SqliteRateRepository(RateRepository):
    def __init__(self, dsn: str = "file:rates.db?mode=ro") -> None:
        self._dsn = dsn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._dsn, uri=True)
        try:
            yield conn
        finally:
            conn.close()

    def rate_for(self, region: str, currency: str) -> Decimal:
        query = "SELECT rate FROM tax_rates WHERE region = ? AND currency = ?"
        with self._connection() as conn:
            row = conn.execute(query, (region, currency)).fetchone()
        if row is None:
            return Decimal("0")
        return Decimal(str(row[0]))
