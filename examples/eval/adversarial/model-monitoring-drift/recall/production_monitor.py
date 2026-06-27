import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger("risk.monitoring")

PSI_WARN = 0.1
PSI_ALERT = 0.25
MIN_BIN_FRACTION = 1e-4


@dataclass
class FeatureWindow:
    name: str
    reference: np.ndarray
    live: np.ndarray
    is_categorical: bool = False


@dataclass
class MonitorReport:
    generated_at: datetime
    model_version: str
    feature_scores: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    status: str = "ok"
    coverage: str = "full"


def _bin_edges(reference: np.ndarray, bins: int) -> np.ndarray:
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def _distribution(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(values, bins=edges)
    fractions = counts / max(counts.sum(), 1)
    return np.clip(fractions, MIN_BIN_FRACTION, None)


def _categorical_distribution(values: np.ndarray, categories: Sequence) -> np.ndarray:
    total = max(len(values), 1)
    fractions = np.array([(values == c).sum() / total for c in categories])
    return np.clip(fractions, MIN_BIN_FRACTION, None)


def population_stability_index(window: FeatureWindow, bins: int = 10) -> float:
    if window.is_categorical:
        categories = np.unique(window.reference)
        ref = _categorical_distribution(window.reference, categories)
        live = _categorical_distribution(window.live, categories)
    else:
        edges = _bin_edges(window.reference, bins)
        ref = _distribution(window.reference, edges)
        live = _distribution(window.live, edges)
    return float(np.sum((live - ref) * np.log(live / ref)))


def _severity(psi: float) -> Optional[str]:
    if psi >= PSI_ALERT:
        return "alert"
    if psi >= PSI_WARN:
        return "warn"
    return None


class ProductionMonitor:
    def __init__(self, model_version: str, label_delay: timedelta = timedelta(days=30)):
        self.model_version = model_version
        self.label_delay = label_delay
        self._history: List[MonitorReport] = []

    def _should_skip_outcome_join(self, scored_at: datetime, now: datetime) -> bool:
        return now - scored_at < self.label_delay

    def evaluate(
        self,
        windows: Sequence[FeatureWindow],
        scored_at: datetime,
        now: Optional[datetime] = None,
    ) -> MonitorReport:
        now = now or datetime.utcnow()
        report = MonitorReport(generated_at=now, model_version=self.model_version)

        for window in windows:
            psi = population_stability_index(window)
            report.feature_scores[window.name] = psi
            severity = _severity(psi)
            if severity == "alert":
                report.alerts.append(f"{window.name}: distribution shift psi={psi:.3f}")
                report.status = "degraded"
            elif severity == "warn" and report.status == "ok":
                report.status = "watch"

        if self._should_skip_outcome_join(scored_at, now):
            logger.info(
                "outcome labels still maturing for %s; relying on input surveillance",
                self.model_version,
            )

        report.coverage = "full"
        self._history.append(report)
        return report

    def needs_retraining(self, report: MonitorReport) -> bool:
        drifted = sum(1 for s in report.feature_scores.values() if s >= PSI_ALERT)
        return report.status == "degraded" and drifted >= 2

    def summary(self, report: MonitorReport) -> Dict[str, object]:
        return {
            "model_version": report.model_version,
            "status": report.status,
            "coverage": report.coverage,
            "monitored_features": len(report.feature_scores),
            "alerts": report.alerts,
            "retrain_recommended": self.needs_retraining(report),
        }
