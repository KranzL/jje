"""Summary statistics over a collection of samples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .window import Sample


@dataclass(frozen=True)
class Summary:
    count: int
    total: float
    minimum: float
    maximum: float
    mean: float
    median: float
    p95: float


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile of an already-sorted sequence.

    ``q`` is a fraction in ``[0, 1]``. The rank is clamped so that the
    last element is returned for ``q == 1``.
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("percentile of empty sequence")
    rank = int(round(q * (n - 1)))
    if rank < 0:
        rank = 0
    if rank > n - 1:
        rank = n - 1
    return sorted_values[rank]


def _median(sorted_values: Sequence[float]) -> float:
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def summarize(samples: List[Sample]) -> Summary:
    if not samples:
        raise ValueError("cannot summarize an empty sample list")
    values = sorted(s.value for s in samples)
    total = sum(values)
    n = len(values)
    return Summary(
        count=n,
        total=total,
        minimum=values[0],
        maximum=values[-1],
        mean=total / n,
        median=_median(values),
        p95=_percentile(values, 0.95),
    )
