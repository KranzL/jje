import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger("risk.monitoring")

PSI_WARN = 0.1
PSI_ALERT = 0.25
MIN_BIN_FRACTION = 1e-4
AUC_FLOOR = 0.72


@dataclass
class FeatureWindow:
    name: str
    reference: np.ndarray
    live: np.ndarray
    is_categorical: bool = False


@dataclass
class OutcomeWindow:
    scored_at: np.ndarray
    predictions: np.ndarray
    labels: np.ndarray


@dataclass
class MonitorReport:
    generated_at: datetime
    model_version: str
    feature_scores: Dict[str, float] = field(default_factory=dict)
    label_psi: Optional[float] = None
    rolling_auc: Optional[float] = None
    alerts: List[str] = field(default_factory=list)
    status: str = "ok"
    coverage: str = "input_only"


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


def _label_psi(reference: np.ndarray, live: np.ndarray) -> float:
    ref = _categorical_distribution(reference, [0, 1])
    cur = _categorical_distribution(live, [0, 1])
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def _auc(predictions: np.ndarray, labels: np.ndarray) -> Optional[float]:
    pos = predictions[labels == 1]
    neg = predictions[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    order = np.argsort(predictions)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(predictions) + 1)
    rank_sum = ranks[labels == 1].sum()
    return float((rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


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

    def _mature(self, scored_at: np.ndarray, now: datetime) -> np.ndarray:
        cutoff = now - self.label_delay
        return scored_at <= np.datetime64(cutoff)

    def evaluate(
        self,
        windows: Sequence[FeatureWindow],
        outcomes: OutcomeWindow,
        reference_labels: np.ndarray,
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

        matured = self._mature(outcomes.scored_at, now)
        if matured.any():
            labels = outcomes.labels[matured]
            preds = outcomes.predictions[matured]
            report.label_psi = _label_psi(reference_labels, labels)
            report.rolling_auc = _auc(preds, labels)
            if report.label_psi is not None and report.label_psi >= PSI_ALERT:
                report.alerts.append(f"label prior shift psi={report.label_psi:.3f}")
                report.status = "degraded"
            if report.rolling_auc is not None and report.rolling_auc < AUC_FLOOR:
                report.alerts.append(f"discrimination decay auc={report.rolling_auc:.3f}")
                report.status = "degraded"
            report.coverage = "input_and_outcome"
        else:
            logger.warning(
                "no matured labels for %s; outcome surface unobserved this cycle",
                self.model_version,
            )
            report.coverage = "input_only"
            if report.status == "ok":
                report.status = "watch"

        self._history.append(report)
        return report

    def needs_retraining(self, report: MonitorReport) -> bool:
        if report.rolling_auc is not None and report.rolling_auc < AUC_FLOOR:
            return True
        drifted = sum(1 for s in report.feature_scores.values() if s >= PSI_ALERT)
        return report.status == "degraded" and drifted >= 2

    def summary(self, report: MonitorReport) -> Dict[str, object]:
        return {
            "model_version": report.model_version,
            "status": report.status,
            "coverage": report.coverage,
            "monitored_features": len(report.feature_scores),
            "label_psi": report.label_psi,
            "rolling_auc": report.rolling_auc,
            "alerts": report.alerts,
            "retrain_recommended": self.needs_retraining(report),
        }
