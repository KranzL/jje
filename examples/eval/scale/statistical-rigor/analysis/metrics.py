from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


PRIMARY_METRIC = "d7_active_minutes"

SECONDARY_METRICS = [
    "d7_sessions",
    "d7_retained",
    "d14_retained",
    "messages_sent",
    "friends_added",
    "search_queries",
    "feed_dwell_seconds",
]


@dataclass(frozen=True)
class MetricFrame:
    metric: str
    treatment: np.ndarray
    control: np.ndarray


def _arm_values(df: pd.DataFrame, metric: str, arm: str) -> np.ndarray:
    mask = df["arm"] == arm
    return df.loc[mask, metric].to_numpy(dtype=float)


def build_metric_frames(df: pd.DataFrame, metrics: list[str]) -> list[MetricFrame]:
    frames = []
    for metric in metrics:
        if metric not in df.columns:
            raise KeyError(f"missing metric column: {metric}")
        frames.append(
            MetricFrame(
                metric=metric,
                treatment=_arm_values(df, metric, "treatment"),
                control=_arm_values(df, metric, "control"),
            )
        )
    return frames


def relative_lift(treatment: np.ndarray, control: np.ndarray) -> float:
    base = control.mean()
    if base == 0:
        return float("nan")
    return float((treatment.mean() - base) / base)


def winsorize(values: np.ndarray, limit: float = 0.99) -> np.ndarray:
    cap = np.quantile(values, limit)
    return np.minimum(values, cap)


def summarize(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for frame in build_metric_frames(df, metrics):
        rows.append(
            {
                "metric": frame.metric,
                "treatment_mean": frame.treatment.mean(),
                "control_mean": frame.control.mean(),
                "relative_lift": relative_lift(frame.treatment, frame.control),
                "n_treatment": frame.treatment.size,
                "n_control": frame.control.size,
            }
        )
    return pd.DataFrame(rows)
