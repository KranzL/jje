from __future__ import annotations

from alerting.dispatcher import AlertDispatcher
from alerting.enrichment import RunbookEnricher
from alerting.models import Alert, Severity


class FakeChannel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sent: list[Alert] = []

    def send(self, alert: Alert) -> str:
        self.sent.append(alert)
        return f"{self.name}-ok"


def make_alert(severity: Severity = Severity.CRITICAL, **labels: str) -> Alert:
    return Alert(
        rule_id="HighErrorRate",
        summary="error rate above threshold",
        severity=severity,
        labels=labels,
    )


def test_dispatch_fans_out_to_all_channels() -> None:
    a, b = FakeChannel("slack"), FakeChannel("pagerduty")
    dispatcher = AlertDispatcher(channels=[a, b])

    results = dispatcher.dispatch(make_alert(service="checkout"))

    assert {r.channel for r in results} == {"slack", "pagerduty"}
    assert all(r.ok for r in results)
    assert len(a.sent) == 1 and len(b.sent) == 1


def test_muted_alerts_are_not_routed() -> None:
    a = FakeChannel("slack")
    dispatcher = AlertDispatcher(channels=[a])

    results = dispatcher.dispatch(make_alert(muted="true"))

    assert results == []
    assert a.sent == []


def test_min_severity_filters_low_priority() -> None:
    a = FakeChannel("slack")
    dispatcher = AlertDispatcher(channels=[a], min_severity=Severity.WARNING)

    results = dispatcher.dispatch(make_alert(severity=Severity.INFO))

    assert results == []


def test_runbook_enricher_adds_label() -> None:
    a = FakeChannel("slack")
    enricher = RunbookEnricher({"HighErrorRate": "https://runbooks/he"})
    dispatcher = AlertDispatcher(channels=[a], enrichers=[enricher])

    dispatcher.dispatch(make_alert())

    assert a.sent[0].labels["runbook_url"] == "https://runbooks/he"
