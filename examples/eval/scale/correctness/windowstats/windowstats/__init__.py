"""windowstats: sliding time-window event aggregation.

This package keeps an append-ordered log of timestamped samples and
exposes half-open range queries, bucketed rollups, and retention-based
eviction of stale samples.
"""

from .window import SlidingWindow, Sample
from .buckets import BucketGrid, bucket_index
from .aggregate import summarize, Summary
from .retention import RetentionPolicy

__all__ = [
    "SlidingWindow",
    "Sample",
    "BucketGrid",
    "bucket_index",
    "summarize",
    "Summary",
    "RetentionPolicy",
]

__version__ = "0.4.0"
