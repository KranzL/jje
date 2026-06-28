from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FeatureDriftResult:
    feature: str
    metric: str
    statistic: float
    threshold: float
    drifted: bool


def _bin_edges(reference: np.ndarray, bins: int) -> np.ndarray:
    quantiles = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    bins: int = 10,
    eps: float = 1e-6,
) -> float:
    edges = _bin_edges(reference, bins)
    ref_hist, _ = np.histogram(reference, bins=edges)
    cur_hist, _ = np.histogram(current, bins=edges)

    ref_frac = ref_hist / max(ref_hist.sum(), 1)
    cur_frac = cur_hist / max(cur_hist.sum(), 1)

    ref_frac = np.clip(ref_frac, eps, None)
    cur_frac = np.clip(cur_frac, eps, None)

    return float(np.sum((cur_frac - ref_frac) * np.log(cur_frac / ref_frac)))


def categorical_jensen_shannon(
    reference: np.ndarray,
    current: np.ndarray,
    eps: float = 1e-6,
) -> float:
    categories = np.union1d(reference, current)
    ref_counts = np.array([(reference == c).sum() for c in categories], dtype=float)
    cur_counts = np.array([(current == c).sum() for c in categories], dtype=float)

    p = np.clip(ref_counts / max(ref_counts.sum(), 1), eps, None)
    q = np.clip(cur_counts / max(cur_counts.sum(), 1), eps, None)
    m = 0.5 * (p + q)

    def _kl(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.sum(a * np.log(a / b)))

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def evaluate_numeric_feature(
    feature: str,
    reference: np.ndarray,
    current: np.ndarray,
    threshold: float,
    bins: int = 10,
) -> FeatureDriftResult:
    statistic = population_stability_index(reference, current, bins=bins)
    return FeatureDriftResult(
        feature=feature,
        metric="psi",
        statistic=statistic,
        threshold=threshold,
        drifted=statistic >= threshold,
    )


def evaluate_categorical_feature(
    feature: str,
    reference: np.ndarray,
    current: np.ndarray,
    threshold: float,
) -> FeatureDriftResult:
    statistic = categorical_jensen_shannon(reference, current)
    return FeatureDriftResult(
        feature=feature,
        metric="js_divergence",
        statistic=statistic,
        threshold=threshold,
        drifted=statistic >= threshold,
    )
