"""Retention policy for evicting stale samples from a window."""

from __future__ import annotations

from dataclasses import dataclass

from .window import SlidingWindow


@dataclass(frozen=True)
class RetentionPolicy:
    """Keep only samples within ``horizon`` seconds of the reference time.

    A sample with timestamp ``ts`` is retained while
    ``ts >= now - horizon``; anything strictly older is dropped.
    """

    horizon: float

    def __post_init__(self) -> None:
        if self.horizon <= 0:
            raise ValueError(f"horizon must be positive, got {self.horizon}")

    def cutoff(self, now: float) -> float:
        return now - self.horizon

    def apply(self, window: SlidingWindow, now: float) -> int:
        """Evict samples older than the cutoff; return the number dropped."""
        return window.drop_before(self.cutoff(now))

    def retained_span(self, now: float) -> float:
        return self.horizon
