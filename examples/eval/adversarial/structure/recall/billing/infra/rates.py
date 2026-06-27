import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from typing import Iterator

_DSN = "file:rates.db?mode=ro"


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_DSN, uri=True)
    try:
        yield conn
    finally:
        conn.close()


def resolve_region_rate(region: str, currency: str) -> Decimal:
    query = "SELECT rate FROM tax_rates WHERE region = ? AND currency = ?"
    with _connection() as conn:
        row = conn.execute(query, (region, currency)).fetchone()
    if row is None:
        return Decimal("0")
    return Decimal(str(row[0]))
