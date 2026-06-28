from __future__ import annotations

import numpy as np
from scipy import stats


def obrien_fleming_alpha(information_fraction: float, alpha: float) -> float:
    if information_fraction <= 0.0:
        return 0.0
    t = min(information_fraction, 1.0)
    z_half = stats.norm.ppf(1.0 - alpha / 2.0)
    spent = 2.0 * (1.0 - stats.norm.cdf(z_half / np.sqrt(t)))
    return float(spent)


def boundary_z(information_fraction: float, alpha: float) -> float:
    spent = obrien_fleming_alpha(information_fraction, alpha)
    spent = max(spent, 1e-12)
    return float(stats.norm.ppf(1.0 - spent / 2.0))


def evaluate_look(z_stat: float, look_index: int, schedule: list[int], alpha: float) -> dict:
    total = schedule[-1]
    info_fraction = schedule[look_index] / total
    crit = boundary_z(info_fraction, alpha)
    return {
        "look": schedule[look_index],
        "information_fraction": info_fraction,
        "boundary_z": crit,
        "reject": bool(abs(z_stat) >= crit),
    }
