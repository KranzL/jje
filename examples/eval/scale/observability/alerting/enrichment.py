from __future__ import annotations

import logging
from typing import Protocol

import requests

from . import metrics
from .models import Alert

logger = logging.getLogger(__name__)


class Enricher(Protocol):
    name: str

    def labels_for(self, alert: Alert) -> dict[str, str]: ...


class OwnerRegistryEnricher:
    name = "owner_registry"

    def __init__(self, base_url: str, session: requests.Session, timeout: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._timeout = timeout

    def labels_for(self, alert: Alert) -> dict[str, str]:
        service = alert.labels.get("service")
        if not service:
            return {}
        resp = self._session.get(
            f"{self._base_url}/owners/{service}",
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        out = {}
        if payload.get("team"):
            out["team"] = str(payload["team"])
        if payload.get("oncall"):
            out["oncall"] = str(payload["oncall"])
        return out


class RunbookEnricher:
    name = "runbook"

    def __init__(self, index: dict[str, str]) -> None:
        self._index = index

    def labels_for(self, alert: Alert) -> dict[str, str]:
        url = self._index.get(alert.rule_id)
        return {"runbook_url": url} if url else {}


def enrich(alert: Alert, enrichers: list[Enricher]) -> Alert:
    enriched = alert
    for enricher in enrichers:
        try:
            extra = enricher.labels_for(enriched)
        except Exception:
            metrics.enrich_failures.inc(enricher=enricher.name)
            logger.warning(
                "enrichment failed; continuing without %s labels",
                enricher.name,
                exc_info=True,
            )
            continue
        if extra:
            enriched = enriched.with_labels(extra)
            metrics.alerts_enriched.inc(enricher=enricher.name)
            logger.debug("applied %d labels from %s", len(extra), enricher.name)
    return enriched
