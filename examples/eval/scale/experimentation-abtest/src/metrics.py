from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MetricSample:
    name: str
    grain: str
    numerator: np.ndarray
    denominator: np.ndarray
    unit_id: np.ndarray


def checkout_starts_per_user(users: pd.DataFrame, variant: str) -> MetricSample:
    rows = users[users["variant"] == variant]
    return MetricSample(
        name="checkout_starts_per_user",
        grain="user",
        numerator=rows["checkout_starts"].to_numpy(dtype=float),
        denominator=np.ones(len(rows), dtype=float),
        unit_id=rows["user_id"].to_numpy(),
    )


def add_to_cart_rate(users: pd.DataFrame, variant: str) -> MetricSample:
    rows = users[users["variant"] == variant]
    converted = (rows["checkout_starts"] > 0).to_numpy(dtype=float)
    return MetricSample(
        name="add_to_cart_rate",
        grain="user",
        numerator=converted,
        denominator=np.ones(len(rows), dtype=float),
        unit_id=rows["user_id"].to_numpy(),
    )


def revenue_per_session(sessions: pd.DataFrame, variant: str) -> MetricSample:
    rows = sessions[sessions["variant"] == variant]
    return MetricSample(
        name="revenue_per_session",
        grain="session",
        numerator=rows["revenue"].to_numpy(dtype=float),
        denominator=np.ones(len(rows), dtype=float),
        unit_id=rows["session_id"].to_numpy(),
    )


def point_estimate(sample: MetricSample) -> float:
    return float(sample.numerator.sum() / sample.denominator.sum())


def relative_lift(control: MetricSample, treatment: MetricSample) -> float:
    base = point_estimate(control)
    if base == 0.0:
        return float("nan")
    return point_estimate(treatment) / base - 1.0
