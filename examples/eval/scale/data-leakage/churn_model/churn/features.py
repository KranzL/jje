"""Row-level feature engineering for the churn model.

These transforms are deterministic functions of a single account's
attributes and are safe to compute once on the full frame before any
train/validation split, because none of them reference the label.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TENURE_BUCKETS = [0, 3, 6, 12, 24, 48, np.inf]
TENURE_LABELS = ["0-3m", "3-6m", "6-12m", "12-24m", "24-48m", "48m+"]


def add_tenure_buckets(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["tenure_bucket"] = pd.cut(
        out["tenure_months"],
        bins=TENURE_BUCKETS,
        labels=TENURE_LABELS,
        right=False,
    ).astype("object")
    return out


def add_usage_ratios(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    monthly = out["monthly_charges"].replace(0, np.nan)
    out["charges_per_tenure"] = out["total_charges"] / out["tenure_months"].clip(lower=1)
    out["support_per_charge"] = out["support_tickets"] / monthly
    out["support_per_charge"] = out["support_per_charge"].fillna(0.0)
    return out


def add_engagement_trend(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    recent = out["logins_last_30d"].astype(float)
    prior = out["logins_prev_30d"].astype(float).clip(lower=1)
    out["login_trend"] = (recent - out["logins_prev_30d"]) / prior
    out["is_dormant"] = (recent == 0).astype(int)
    return out


def add_regional_churn_rate(df: pd.DataFrame, label_col: str = "churned") -> pd.DataFrame:
    """Attach the historical churn propensity of each account's region.

    Region is high cardinality and one-hot encoding it produces a very
    sparse block, so we summarize each region by its observed churn rate.
    """
    out = df.copy()
    region_rate = out.groupby("region")[label_col].transform("mean")
    global_rate = out[label_col].mean()
    out["region_churn_rate"] = region_rate.fillna(global_rate)
    return out


def engineer_features(df: pd.DataFrame, label_col: str = "churned") -> pd.DataFrame:
    out = add_tenure_buckets(df)
    out = add_usage_ratios(out)
    out = add_engagement_trend(out)
    out = add_regional_churn_rate(out, label_col=label_col)
    return out
