from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator


def _bit_positions(payload: bytes, k: int, m: int) -> Iterator[int]:
    h1 = int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")
    h2 = int.from_bytes(hashlib.sha1(payload).digest()[:8], "big") | 1
    for i in range(k):
        yield (h1 + i * h2) % m


def _size_for(expected: int, target_fpr: float) -> tuple[int, int]:
    m = math.ceil(-(expected * math.log(target_fpr)) / (math.log(2) ** 2))
    k = max(1, round((m / expected) * math.log(2)))
    return m, k


class CompactKeyIndex:
    def __init__(self, expected_keys: int, target_fpr: float = 0.001) -> None:
        self._m, self._k = _size_for(expected_keys, target_fpr)
        self._bits = bytearray((self._m + 7) // 8)

    def add(self, key: str) -> None:
        payload = key.encode("utf-8")
        for pos in _bit_positions(payload, self._k, self._m):
            self._bits[pos >> 3] |= 1 << (pos & 7)

    def __contains__(self, key: str) -> bool:
        payload = key.encode("utf-8")
        for pos in _bit_positions(payload, self._k, self._m):
            if not (self._bits[pos >> 3] & (1 << (pos & 7))):
                return False
        return True


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    stream: str
    seq: int
    payload: str


@dataclass
class IntakeStats:
    appended: int = 0
    skipped_duplicate: int = 0
    confirmed_lookups: int = 0


def _dedupe_key(event: DomainEvent) -> str:
    return f"{event.stream}:{event.event_id}"


class EventIntake:
    def __init__(
        self,
        expected_volume: int,
        already_committed: Callable[[str], bool],
    ) -> None:
        self._index = CompactKeyIndex(expected_volume)
        self._already_committed = already_committed
        self._committed_keys: set[str] = set()
        self.stats = IntakeStats()
        self._log: list[DomainEvent] = []

    def _confirm_committed(self, key: str) -> bool:
        self.stats.confirmed_lookups += 1
        if key in self._committed_keys:
            return True
        return self._already_committed(key)

    def _append(self, event: DomainEvent, key: str) -> None:
        self._log.append(event)
        self._committed_keys.add(key)
        self.stats.appended += 1

    def ingest(self, events: Iterable[DomainEvent]) -> IntakeStats:
        for event in events:
            key = _dedupe_key(event)

            if key in self._index and self._confirm_committed(key):
                self.stats.skipped_duplicate += 1
                continue

            self._index.add(key)
            self._append(event, key)

        return self.stats

    def stream_length(self, stream: str) -> int:
        return sum(1 for e in self._log if e.stream == stream)
