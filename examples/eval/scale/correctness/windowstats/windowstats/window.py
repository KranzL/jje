"""Append-ordered sliding window of timestamped samples.

Timestamps are floating-point seconds since an arbitrary epoch. Samples
are appended in non-decreasing timestamp order; range queries are served
with binary search over the maintained timestamp index.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Sample:
    ts: float
    value: float
    label: Optional[str] = None


class SlidingWindow:
    """A growable, time-ordered collection of :class:`Sample` records.

    All range queries use half-open intervals ``[start, end)`` unless a
    method name explicitly says otherwise. The window never reorders
    samples; callers must append in non-decreasing timestamp order.
    """

    def __init__(self, samples: Optional[Iterable[Sample]] = None) -> None:
        self._samples: List[Sample] = []
        self._ts: List[float] = []
        if samples is not None:
            for s in samples:
                self.append(s)

    def __len__(self) -> int:
        return len(self._samples)

    def append(self, sample: Sample) -> None:
        if self._ts and sample.ts < self._ts[-1]:
            raise ValueError(
                f"out-of-order append: {sample.ts} < {self._ts[-1]}"
            )
        self._samples.append(sample)
        self._ts.append(sample.ts)

    def extend(self, samples: Iterable[Sample]) -> None:
        for s in samples:
            self.append(s)

    def first_at_or_after(self, ts: float) -> int:
        """Index of the earliest sample with ``sample.ts >= ts``."""
        return bisect.bisect_left(self._ts, ts)

    def query(self, start: float, end: float) -> List[Sample]:
        """Return samples whose timestamp lies in half-open ``[start, end)``.

        ``start`` is inclusive and ``end`` is exclusive, matching the
        convention used by the bucket grid and retention policy.
        """
        if end < start:
            raise ValueError(f"empty interval: end {end} < start {start}")
        lo = bisect.bisect_left(self._ts, start)
        hi = bisect.bisect_right(self._ts, end)
        return self._samples[lo:hi]

    def query_inclusive(self, start: float, end: float) -> List[Sample]:
        """Return samples whose timestamp lies in closed ``[start, end]``."""
        if end < start:
            raise ValueError(f"empty interval: end {end} < start {start}")
        lo = bisect.bisect_left(self._ts, start)
        hi = bisect.bisect_right(self._ts, end)
        return self._samples[lo:hi]

    def values_between(self, start: float, end: float) -> List[float]:
        return [s.value for s in self.query(start, end)]

    def latest(self, n: int) -> List[Sample]:
        if n <= 0:
            return []
        return self._samples[-n:]

    def span(self) -> float:
        if not self._ts:
            return 0.0
        return self._ts[-1] - self._ts[0]

    def drop_before(self, ts: float) -> int:
        """Discard samples strictly older than ``ts``; return drop count."""
        cut = bisect.bisect_left(self._ts, ts)
        if cut:
            del self._samples[:cut]
            del self._ts[:cut]
        return cut
