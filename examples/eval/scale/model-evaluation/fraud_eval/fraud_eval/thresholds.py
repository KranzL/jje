from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .metrics import precision_at_threshold, recall_at_threshold


@dataclass(frozen=True)
class OperatingPoint:
    threshold: float
    precision: float
    recall: float


def _candidate_thresholds(scores_val: np.ndarray, grid: int) -> np.ndarray:
    lo = float(np.min(scores_val))
    hi = float(np.max(scores_val))
    if hi <= lo:
        return np.array([lo])
    return np.linspace(lo, hi, grid)


def select_operating_threshold(
    y_val,
    scores_val,
    target_precision: float = 0.5,
    grid: int = 200,
) -> OperatingPoint:
    """Pick the lowest threshold on the validation split that still clears the
    target precision, maximizing recall subject to that precision floor.

    The threshold is derived purely from the validation fold; the held-out test
    fold is never consulted here so the operating point stays unbiased.
    """
    y = np.asarray(y_val).astype(int)
    s = np.asarray(scores_val, dtype=float)
    candidates = _candidate_thresholds(s, grid)

    best: OperatingPoint | None = None
    for t in candidates:
        prec = precision_at_threshold(y, s, t)
        rec = recall_at_threshold(y, s, t)
        if prec < target_precision:
            continue
        if best is None or rec > best.recall:
            best = OperatingPoint(threshold=float(t), precision=prec, recall=rec)

    if best is None:
        top = float(np.max(s))
        return OperatingPoint(
            threshold=top,
            precision=precision_at_threshold(y, s, top),
            recall=recall_at_threshold(y, s, top),
        )
    return best
