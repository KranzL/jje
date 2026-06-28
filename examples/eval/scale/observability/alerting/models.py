from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


class Severity(enum.IntEnum):
    INFO = 10
    WARNING = 20
    CRITICAL = 30

    @classmethod
    def parse(cls, raw: str) -> "Severity":
        try:
            return cls[raw.strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unknown severity: {raw!r}") from exc


@dataclass(frozen=True)
class Alert:
    rule_id: str
    summary: str
    severity: Severity
    labels: dict[str, str] = field(default_factory=dict)
    fingerprint: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)

    def with_labels(self, extra: dict[str, str]) -> "Alert":
        merged = dict(self.labels)
        merged.update(extra)
        return Alert(
            rule_id=self.rule_id,
            summary=self.summary,
            severity=self.severity,
            labels=merged,
            fingerprint=self.fingerprint,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    ok: bool
    detail: Optional[str] = None
    latency_ms: float = 0.0
