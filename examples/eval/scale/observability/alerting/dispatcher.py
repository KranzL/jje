from __future__ import annotations

import logging
import time

from . import metrics
from .channels import Channel
from .enrichment import Enricher, enrich
from .models import Alert, DeliveryResult, Severity

logger = logging.getLogger(__name__)


class AlertDispatcher:
    def __init__(
        self,
        channels: list[Channel],
        enrichers: list[Enricher] | None = None,
        min_severity: Severity = Severity.INFO,
    ) -> None:
        self._channels = channels
        self._enrichers = enrichers or []
        self._min_severity = min_severity

    def _route(self, alert: Alert) -> list[Channel]:
        if alert.severity < self._min_severity:
            return []
        if alert.labels.get("muted") == "true":
            logger.info("alert %s muted by label; not routing", alert.rule_id)
            return []
        return list(self._channels)

    def dispatch(self, alert: Alert) -> list[DeliveryResult]:
        enriched = enrich(alert, self._enrichers)
        targets = self._route(enriched)
        if not targets:
            logger.info("no channels for alert %s sev=%s", enriched.rule_id, enriched.severity.name)
            return []

        results: list[DeliveryResult] = []
        for channel in targets:
            started = time.perf_counter()
            try:
                detail = channel.send(enriched)
            except Exception:
                continue
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            metrics.deliveries.inc(channel=channel.name, outcome="ok")
            metrics.delivery_latency.observe(elapsed_ms)
            logger.info(
                "dispatched %s via %s in %.1fms",
                enriched.rule_id,
                channel.name,
                elapsed_ms,
            )
            results.append(
                DeliveryResult(
                    channel=channel.name,
                    ok=True,
                    detail=detail,
                    latency_ms=elapsed_ms,
                )
            )
        return results

    def dispatch_batch(self, alerts: list[Alert]) -> dict[str, list[DeliveryResult]]:
        out: dict[str, list[DeliveryResult]] = {}
        for alert in alerts:
            out[alert.fingerprint] = self.dispatch(alert)
        return out
