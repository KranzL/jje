from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TestResult:
    name: str
    estimate: float
    p_value: float
    ci_low: float
    ci_high: float
    n_treatment: int
    n_control: int


def welch_ttest(treatment: Sequence[float], control: Sequence[float]) -> TestResult:
    t = np.asarray(treatment, dtype=float)
    c = np.asarray(control, dtype=float)
    stat, p = stats.ttest_ind(t, c, equal_var=False)
    diff = float(t.mean() - c.mean())
    se = np.sqrt(t.var(ddof=1) / t.size + c.var(ddof=1) / c.size)
    z = stats.norm.ppf(0.975)
    return TestResult(
        name="",
        estimate=diff,
        p_value=float(p),
        ci_low=diff - z * se,
        ci_high=diff + z * se,
        n_treatment=int(t.size),
        n_control=int(c.size),
    )


def bonferroni(p_values: Sequence[float]) -> list[float]:
    m = len(p_values)
    return [min(1.0, p * m) for p in p_values]


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    m = len(p_values)
    order = np.argsort(p_values)
    ranked = np.asarray(p_values, dtype=float)[order]
    thresholds = (np.arange(1, m + 1) / m) * alpha
    passed = ranked <= thresholds
    if not passed.any():
        rejected = np.zeros(m, dtype=bool)
    else:
        max_k = np.max(np.where(passed)[0])
        rejected = np.zeros(m, dtype=bool)
        rejected[: max_k + 1] = True
    out = np.zeros(m, dtype=bool)
    out[order] = rejected
    return out.tolist()


def holm(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    m = len(p_values)
    order = np.argsort(p_values)
    ranked = np.asarray(p_values, dtype=float)[order]
    out = np.zeros(m, dtype=bool)
    for i, p in enumerate(ranked):
        if p <= alpha / (m - i):
            out[order[i]] = True
        else:
            break
    return out.tolist()
