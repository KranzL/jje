from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReferenceWindow:
    start: date
    end: date
    frame: pd.DataFrame


class ReferenceStore:
    def __init__(self, history: pd.DataFrame, timestamp_col: str = "event_date"):
        if timestamp_col not in history.columns:
            raise KeyError(f"missing timestamp column {timestamp_col!r}")
        self._history = history
        self._timestamp_col = timestamp_col

    def baseline_window(
        self,
        as_of: date,
        window_days: int,
        label_lag_days: int,
    ) -> ReferenceWindow:
        end = as_of - timedelta(days=label_lag_days)
        start = end - timedelta(days=window_days)
        mask = (
            (self._history[self._timestamp_col] > pd.Timestamp(start))
            & (self._history[self._timestamp_col] <= pd.Timestamp(end))
        )
        frame = self._history.loc[mask]
        return ReferenceWindow(start=start, end=end, frame=frame)

    def current_window(
        self,
        as_of: date,
        window_days: int,
    ) -> ReferenceWindow:
        end = as_of
        start = end - timedelta(days=window_days)
        mask = (
            (self._history[self._timestamp_col] > pd.Timestamp(start))
            & (self._history[self._timestamp_col] <= pd.Timestamp(end))
        )
        frame = self._history.loc[mask]
        return ReferenceWindow(start=start, end=end, frame=frame)

    @staticmethod
    def column_values(window: ReferenceWindow, column: str) -> np.ndarray:
        return window.frame[column].to_numpy()
