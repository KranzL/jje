from __future__ import annotations

import numpy as np
import pandas as pd


def apply_cuped(users: pd.DataFrame, covariate: str) -> pd.DataFrame:
    if covariate not in users.columns:
        raise ValueError(f"missing CUPED covariate: {covariate}")

    x = users[covariate].to_numpy(dtype=float)
    y = users["checkout_starts"].to_numpy(dtype=float)
    x_centered = x - x.mean()

    var_x = float(np.var(x_centered, ddof=1))
    if var_x == 0.0:
        users = users.copy()
        users["checkout_starts_cuped"] = y
        return users

    theta = float(np.cov(y, x, ddof=1)[0, 1] / var_x)
    adjusted = y - theta * x_centered

    out = users.copy()
    out["checkout_starts_cuped"] = adjusted
    return out


def variance_reduction(users: pd.DataFrame, covariate: str) -> float:
    x = users[covariate].to_numpy(dtype=float)
    y = users["checkout_starts"].to_numpy(dtype=float)
    rho = float(np.corrcoef(x, y)[0, 1])
    return rho ** 2
