from __future__ import annotations

import logging
import time
from typing import Callable, Protocol, TypeVar

import requests

from .models import Alert, Severity

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ChannelError(RuntimeError):
    pass


class Channel(Protocol):
    name: str

    def send(self, alert: Alert) -> str: ...


def _with_retry(fn: Callable[[], T], attempts: int, backoff: float) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except (requests.RequestException, ChannelError) as exc:
            last_exc = exc
            logger.warning("attempt %d/%d failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(backoff * attempt)
    assert last_exc is not None
    raise last_exc


class SlackChannel:
    name = "slack"

    def __init__(self, webhook_url: str, session: requests.Session, attempts: int = 3) -> None:
        self._webhook_url = webhook_url
        self._session = session
        self._attempts = attempts

    def _post(self, alert: Alert) -> str:
        emoji = {
            Severity.INFO: ":information_source:",
            Severity.WARNING: ":warning:",
            Severity.CRITICAL: ":rotating_light:",
        }[alert.severity]
        body = {
            "text": f"{emoji} *{alert.rule_id}* — {alert.summary}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": alert.summary},
                }
            ],
        }
        resp = self._session.post(self._webhook_url, json=body, timeout=5.0)
        if resp.status_code >= 400:
            raise ChannelError(f"slack returned {resp.status_code}")
        return resp.text

    def send(self, alert: Alert) -> str:
        return _with_retry(lambda: self._post(alert), self._attempts, backoff=0.5)


class PagerDutyChannel:
    name = "pagerduty"

    def __init__(self, routing_key: str, session: requests.Session, attempts: int = 3) -> None:
        self._routing_key = routing_key
        self._session = session
        self._attempts = attempts
        self._endpoint = "https://events.pagerduty.com/v2/enqueue"

    def _post(self, alert: Alert) -> str:
        if alert.severity < Severity.WARNING:
            logger.debug("skipping pagerduty for low severity %s", alert.rule_id)
            return "skipped"
        body = {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "dedup_key": alert.fingerprint,
            "payload": {
                "summary": alert.summary,
                "severity": "critical" if alert.severity == Severity.CRITICAL else "warning",
                "source": alert.labels.get("service", "unknown"),
                "custom_details": dict(alert.labels),
            },
        }
        resp = self._session.post(self._endpoint, json=body, timeout=5.0)
        if resp.status_code >= 400:
            raise ChannelError(f"pagerduty returned {resp.status_code}")
        return resp.json().get("dedup_key", alert.fingerprint)

    def send(self, alert: Alert) -> str:
        return _with_retry(lambda: self._post(alert), self._attempts, backoff=0.5)
