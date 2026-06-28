from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .metrics import MetricSample


@dataclass(frozen=True)
class Estimate:
    name: str
    point: float
    se: float
    n: int

    def ci(self, alpha: float) -> tuple[float, float]:
        z = stats.norm.ppf(1.0 - alpha / 2.0)
        return self.point - z * self.se, self.point + z * self.se


def mean_estimate(sample: MetricSample) -> Estimate:
    values = sample.numerator
    n = len(values)
    se = float(np.std(values, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    return Estimate(name=sample.name, point=float(values.mean()), se=se, n=n)


def proportion_estimate(sample: MetricSample) -> Estimate:
    successes = sample.numerator
    n = len(successes)
    p = float(successes.mean())
    se = float(np.sqrt(p * (1.0 - p) / n)) if n > 0 else float("nan")
    return Estimate(name=sample.name, point=p, se=se, n=n)


def clustered_ratio_estimate(
    numerator: np.ndarray,
    denominator: np.ndarray,
    cluster_id: np.ndarray,
    name: str,
) -> Estimate:
    frame = pd.DataFrame(
        {"num": numerator, "den": denominator, "cluster": cluster_id}
    )
    grouped = frame.groupby("cluster", as_index=False).agg(
        num=("num", "sum"), den=("den", "sum")
    )
    num = grouped["num"].to_numpy(dtype=float)
    den = grouped["den"].to_numpy(dtype=float)
    n = len(grouped)
    r = num.sum() / den.sum()
    den_mean = den.mean()
    influence = (num - r * den) / den_mean
    se = float(np.std(influence, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    return Estimate(name=name, point=float(r), se=se, n=n)


def estimate_for(sample: MetricSample) -> Estimate:
    if sample.name == "add_to_cart_rate":
        return proportion_estimate(sample)
    if sample.grain == "user":
        return mean_estimate(sample)
    return mean_estimate(sample)


def difference_test(control: Estimate, treatment: Estimate, alpha: float) -> dict:
    diff = treatment.point - control.point
    se_diff = float(np.sqrt(control.se ** 2 + treatment.se ** 2))
    z = diff / se_diff if se_diff > 0 else float("nan")
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    margin = stats.norm.ppf(1.0 - alpha / 2.0) * se_diff
    return {
        "abs_diff": diff,
        "se_diff": se_diff,
        "z": z,
        "p_value": p_value,
        "ci_low": diff - margin,
        "ci_high": diff + margin,
    }
