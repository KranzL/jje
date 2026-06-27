from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Iterable, Iterator


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
        self._added = 0

    def add(self, key: str) -> None:
        payload = key.encode("utf-8")
        for pos in _bit_positions(payload, self._k, self._m):
            self._bits[pos >> 3] |= 1 << (pos & 7)
        self._added += 1

    def __contains__(self, key: str) -> bool:
        payload = key.encode("utf-8")
        for pos in _bit_positions(payload, self._k, self._m):
            if not (self._bits[pos >> 3] & (1 << (pos & 7))):
                return False
        return True

    @property
    def load(self) -> float:
        return self._added / max(1, self._m)


@dataclass(frozen=True)
class JournalEntry:
    entry_id: str
    account: str
    amount_cents: int
    posted_at: str


@dataclass
class IntakeStats:
    accepted: int = 0
    skipped_duplicate: int = 0
    rejected_invalid: int = 0
    posted_accounts: set[str] = field(default_factory=set)


def _is_valid(entry: JournalEntry) -> bool:
    if not entry.entry_id or not entry.account:
        return False
    if entry.amount_cents == 0:
        return False
    return True


def _dedupe_key(entry: JournalEntry) -> str:
    return f"{entry.account}:{entry.entry_id}"


class JournalIntake:
    def __init__(self, expected_volume: int) -> None:
        self._index = CompactKeyIndex(expected_volume)
        self.stats = IntakeStats()
        self._ledger: list[JournalEntry] = []

    def _post(self, entry: JournalEntry) -> None:
        self._ledger.append(entry)
        self.stats.accepted += 1
        self.stats.posted_accounts.add(entry.account)

    def ingest(self, entries: Iterable[JournalEntry]) -> IntakeStats:
        for entry in entries:
            if not _is_valid(entry):
                self.stats.rejected_invalid += 1
                continue

            key = _dedupe_key(entry)
            if key in self._index:
                self.stats.skipped_duplicate += 1
                continue

            self._index.add(key)
            self._post(entry)

        return self.stats

    def settled_total(self, account: str) -> int:
        return sum(e.amount_cents for e in self._ledger if e.account == account)
