from __future__ import annotations

import threading
from collections import defaultdict


class Counter:
    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._values: dict[tuple[tuple[str, str], ...], int] = defaultdict(int)

    def inc(self, amount: int = 1, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] += amount

    def snapshot(self) -> dict[tuple[tuple[str, str], ...], int]:
        with self._lock:
            return dict(self._values)


class Histogram:
    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._observations: list[float] = []

    def observe(self, value: float) -> None:
        with self._lock:
            self._observations.append(value)

    def count(self) -> int:
        with self._lock:
            return len(self._observations)


alerts_enriched = Counter("alerting_enriched_total")
enrich_failures = Counter("alerting_enrich_failures_total")
deliveries = Counter("alerting_deliveries_total")
delivery_latency = Histogram("alerting_delivery_latency_ms")
