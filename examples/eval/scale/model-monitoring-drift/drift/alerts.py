from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("drift.alerts")


@dataclass(frozen=True)
class Alert:
    surface: str
    detail: str
    statistic: float
    threshold: float


class AlertSink:
    def emit(self, alert: Alert) -> None:
        raise NotImplementedError


class LoggingAlertSink(AlertSink):
    def emit(self, alert: Alert) -> None:
        logger.warning(
            "drift alert surface=%s detail=%s statistic=%.4f threshold=%.4f",
            alert.surface,
            alert.detail,
            alert.statistic,
            alert.threshold,
        )


class CollectingAlertSink(AlertSink):
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def emit(self, alert: Alert) -> None:
        self.alerts.append(alert)
