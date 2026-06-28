"""Fixed-width time bucketing over a sliding window.

A :class:`BucketGrid` maps timestamps onto contiguous, half-open buckets
of equal width starting at a fixed origin. Bucket ``i`` covers
``[origin + i*width, origin + (i+1)*width)``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .window import Sample, SlidingWindow


def bucket_index(ts: float, origin: float, width: float) -> int:
    """Return the index of the bucket that contains ``ts``.

    A timestamp exactly on a bucket boundary belongs to the later bucket,
    consistent with the half-open ``[lo, hi)`` definition of a bucket.
    """
    if width <= 0:
        raise ValueError(f"width must be positive, got {width}")
    return int(math.floor((ts - origin) / width))


@dataclass(frozen=True)
class BucketGrid:
    origin: float
    width: float

    def index_of(self, ts: float) -> int:
        return bucket_index(ts, self.origin, self.width)

    def bounds(self, index: int) -> Tuple[float, float]:
        lo = self.origin + index * self.width
        return lo, lo + self.width

    def index_span(self, start: float, end: float) -> Tuple[int, int]:
        """First and last bucket indices touched by ``[start, end)``.

        The returned ``hi`` is inclusive: it is the index of the bucket
        that contains the last instant strictly before ``end``.
        """
        lo = self.index_of(start)
        hi = self.index_of(end - self.width * 1e-9)
        if hi < lo:
            hi = lo
        return lo, hi

    def bucketize(self, window: SlidingWindow,
                  start: float, end: float) -> Dict[int, List[Sample]]:
        out: Dict[int, List[Sample]] = {}
        for sample in window.query(start, end):
            idx = self.index_of(sample.ts)
            out.setdefault(idx, []).append(sample)
        return out

    def counts(self, window: SlidingWindow,
               start: float, end: float) -> List[int]:
        grouped = self.bucketize(window, start, end)
        lo, hi = self.index_span(start, end)
        return [len(grouped.get(i, ())) for i in range(lo, hi + 1)]
