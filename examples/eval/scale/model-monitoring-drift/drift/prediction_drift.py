from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .feature_drift import population_stability_index


@dataclass(frozen=True)
class PredictionDriftResult:
    metric: str
    statistic: float
    threshold: float
    drifted: bool


def score_distribution_drift(
    reference_scores: np.ndarray,
    current_scores: np.ndarray,
    threshold: float,
    bins: int = 20,
) -> PredictionDriftResult:
    statistic = population_stability_index(
        reference_scores, current_scores, bins=bins
    )
    return PredictionDriftResult(
        metric="score_psi",
        statistic=statistic,
        threshold=threshold,
        drifted=statistic >= threshold,
    )


def positive_rate_shift(
    reference_scores: np.ndarray,
    current_scores: np.ndarray,
    decision_threshold: float,
    tolerance: float,
) -> PredictionDriftResult:
    ref_rate = float((reference_scores >= decision_threshold).mean())
    cur_rate = float((current_scores >= decision_threshold).mean())
    delta = abs(cur_rate - ref_rate)
    return PredictionDriftResult(
        metric="positive_rate_delta",
        statistic=delta,
        threshold=tolerance,
        drifted=delta >= tolerance,
    )
