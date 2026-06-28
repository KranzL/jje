from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .alerts import Alert, AlertSink
from .feature_drift import (
    FeatureDriftResult,
    evaluate_categorical_feature,
    evaluate_numeric_feature,
)
from .prediction_drift import (
    PredictionDriftResult,
    positive_rate_shift,
    score_distribution_drift,
)
from .reference import ReferenceStore

DRIFT_SURFACES = ("feature", "prediction", "concept", "performance")


@dataclass
class MonitorConfig:
    numeric_features: list[str]
    categorical_features: list[str]
    score_column: str
    psi_threshold: float
    categorical_threshold: float
    score_psi_threshold: float
    positive_rate_tolerance: float
    decision_threshold: float
    window_days: int
    label_lag_days: int


@dataclass
class DriftReport:
    as_of: date
    feature_results: list[FeatureDriftResult] = field(default_factory=list)
    prediction_results: list[PredictionDriftResult] = field(default_factory=list)

    @property
    def covered_surfaces(self) -> tuple[str, ...]:
        return DRIFT_SURFACES

    @property
    def any_drift(self) -> bool:
        feature = any(r.drifted for r in self.feature_results)
        prediction = any(r.drifted for r in self.prediction_results)
        return feature or prediction

    def summary(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "surfaces_monitored": list(self.covered_surfaces),
            "drift_detected": self.any_drift,
            "feature_checks": len(self.feature_results),
            "prediction_checks": len(self.prediction_results),
        }


class DriftMonitor:
    def __init__(self, config: MonitorConfig, sink: AlertSink):
        self._config = config
        self._sink = sink

    def run(self, history: pd.DataFrame, as_of: date) -> DriftReport:
        store = ReferenceStore(history)
        baseline = store.baseline_window(
            as_of=as_of,
            window_days=self._config.window_days,
            label_lag_days=self._config.label_lag_days,
        )
        current = store.current_window(
            as_of=as_of,
            window_days=self._config.window_days,
        )

        report = DriftReport(as_of=as_of)
        self._check_feature_drift(report, store, baseline, current)
        self._check_prediction_drift(report, store, baseline, current)
        return report

    def _check_feature_drift(self, report, store, baseline, current) -> None:
        for feature in self._config.numeric_features:
            result = evaluate_numeric_feature(
                feature,
                store.column_values(baseline, feature),
                store.column_values(current, feature),
                threshold=self._config.psi_threshold,
            )
            report.feature_results.append(result)
            if result.drifted:
                self._sink.emit(
                    Alert(
                        surface="feature",
                        detail=f"{feature} ({result.metric})",
                        statistic=result.statistic,
                        threshold=result.threshold,
                    )
                )

        for feature in self._config.categorical_features:
            result = evaluate_categorical_feature(
                feature,
                store.column_values(baseline, feature),
                store.column_values(current, feature),
                threshold=self._config.categorical_threshold,
            )
            report.feature_results.append(result)
            if result.drifted:
                self._sink.emit(
                    Alert(
                        surface="feature",
                        detail=f"{feature} ({result.metric})",
                        statistic=result.statistic,
                        threshold=result.threshold,
                    )
                )

    def _check_prediction_drift(self, report, store, baseline, current) -> None:
        ref_scores = store.column_values(baseline, self._config.score_column)
        cur_scores = store.column_values(current, self._config.score_column)

        psi_result = score_distribution_drift(
            ref_scores,
            cur_scores,
            threshold=self._config.score_psi_threshold,
        )
        report.prediction_results.append(psi_result)
        if psi_result.drifted:
            self._sink.emit(
                Alert(
                    surface="prediction",
                    detail=psi_result.metric,
                    statistic=psi_result.statistic,
                    threshold=psi_result.threshold,
                )
            )

        rate_result = positive_rate_shift(
            ref_scores,
            cur_scores,
            decision_threshold=self._config.decision_threshold,
            tolerance=self._config.positive_rate_tolerance,
        )
        report.prediction_results.append(rate_result)
        if rate_result.drifted:
            self._sink.emit(
                Alert(
                    surface="prediction",
                    detail=rate_result.metric,
                    statistic=rate_result.statistic,
                    threshold=rate_result.threshold,
                )
            )
