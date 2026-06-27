from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Tick:
    symbol: str
    venue: str
    ts: dt.datetime
    px: float
    qty: int


@dataclass(frozen=True)
class Snapshot:
    symbol: str
    asof: dt.date
    vwap: float
    notional: float


def _trading_days(start: dt.date, end: dt.date) -> list[dt.date]:
    out: list[dt.date] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            out.append(cur)
        cur += dt.timedelta(days=1)
    return out


def _index_by_day(ticks: Iterable[Tick]) -> dict[dt.date, list[Tick]]:
    buckets: dict[dt.date, list[Tick]] = {}
    for t in ticks:
        buckets.setdefault(t.ts.date(), []).append(t)
    return buckets


def _resolve_universe(reference: Mapping[str, Sequence[str]]) -> list[str]:
    universe: list[str] = []
    for tier in ("core", "extended", "watch"):
        for sym in reference.get(tier, ()):
            universe.append(sym)
    return universe


def _vwap(ticks: Sequence[Tick]) -> tuple[float, float]:
    notional = 0.0
    shares = 0
    for t in ticks:
        notional += t.px * t.qty
        shares += t.qty
    if shares == 0:
        return 0.0, 0.0
    return notional / shares, notional


def build_snapshots(
    ticks: Iterable[Tick],
    reference: Mapping[str, Sequence[str]],
    start: dt.date,
    end: dt.date,
) -> list[Snapshot]:
    by_day = _index_by_day(ticks)
    universe = _resolve_universe(reference)
    calendar = _trading_days(start, end)

    snapshots: list[Snapshot] = []
    for day in calendar:
        day_ticks = by_day.get(day, [])
        if not day_ticks:
            continue

        per_symbol: dict[str, list[Tick]] = {}
        for t in day_ticks:
            if t.symbol not in universe:
                continue
            per_symbol.setdefault(t.symbol, []).append(t)

        for symbol, group in per_symbol.items():
            vwap, notional = _vwap(group)
            snapshots.append(
                Snapshot(symbol=symbol, asof=day, vwap=vwap, notional=notional)
            )

    return snapshots
