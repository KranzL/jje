from __future__ import annotations

import pandas as pd
from scipy import stats


def sample_ratio_mismatch(exposures: pd.DataFrame, expected_weights: dict) -> dict:
    counts = exposures.groupby("variant")["user_id"].nunique()
    total = int(counts.sum())

    observed = []
    expected = []
    for variant, weight in expected_weights.items():
        observed.append(int(counts.get(variant, 0)))
        expected.append(weight * total)

    chi2, p_value = stats.chisquare(f_obs=observed, f_exp=expected)
    return {
        "observed": dict(zip(expected_weights.keys(), observed)),
        "total": total,
        "chi2": float(chi2),
        "p_value": float(p_value),
        "srm_flag": bool(p_value < 0.001),
    }
