from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class PowerPlan:
    metric: str
    baseline_mean: float
    baseline_std: float
    mde_relative: float
    alpha: float
    power: float
    required_per_arm: int


def sample_size_per_arm(
    baseline_std: float,
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    if effect_size <= 0:
        raise ValueError("effect_size must be positive")
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    n = 2 * ((z_alpha + z_beta) ** 2) * (baseline_std**2) / (effect_size**2)
    return int(np.ceil(n))


def plan_primary_metric(
    metric: str,
    baseline_mean: float,
    baseline_std: float,
    mde_relative: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> PowerPlan:
    effect = baseline_mean * mde_relative
    n = sample_size_per_arm(baseline_std, effect, alpha=alpha, power=power)
    return PowerPlan(
        metric=metric,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        mde_relative=mde_relative,
        alpha=alpha,
        power=power,
        required_per_arm=n,
    )


def achieved_power(
    baseline_std: float,
    observed_effect: float,
    n_per_arm: int,
    alpha: float = 0.05,
) -> float:
    if observed_effect == 0:
        return alpha
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    se = baseline_std * np.sqrt(2.0 / n_per_arm)
    ncp = abs(observed_effect) / se
    return float(stats.norm.cdf(ncp - z_alpha))
