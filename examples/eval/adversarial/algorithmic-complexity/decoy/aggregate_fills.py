from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

import pandas as pd


@dataclass(frozen=True)
class Fill:
    account: str
    symbol: str
    qty: int
    price: float


def _eligible_accounts(roster: Sequence[str]) -> frozenset[str]:
    return frozenset(a.strip().upper() for a in roster if a.strip())


def _chunks(rows: Sequence[Fill], size: int) -> Iterator[Sequence[Fill]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _chunk_frame(rows: Sequence[Fill], allowed: frozenset[str]) -> pd.DataFrame:
    kept = []
    for r in rows:
        if r.account not in allowed:
            continue
        kept.append((r.account, r.symbol, r.qty, r.price, r.qty * r.price))
    return pd.DataFrame(
        kept, columns=["account", "symbol", "qty", "price", "notional"]
    )


def aggregate_fills(
    fills: Iterable[Fill],
    roster: Sequence[str],
    chunk_size: int = 5_000,
) -> pd.DataFrame:
    rows = list(fills)
    allowed = _eligible_accounts(roster)

    frames: list[pd.DataFrame] = []
    for chunk in _chunks(rows, chunk_size):
        frame = _chunk_frame(chunk, allowed)
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return pd.DataFrame(
            columns=["account", "symbol", "qty", "price", "notional"]
        )

    combined = pd.concat(frames, ignore_index=True)
    return (
        combined.groupby(["account", "symbol"], as_index=False)[["qty", "notional"]]
        .sum()
        .sort_values(["account", "symbol"], ignore_index=True)
    )
