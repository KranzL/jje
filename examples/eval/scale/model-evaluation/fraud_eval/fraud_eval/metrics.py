from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass(frozen=True)
class ConfusionCounts:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn


def _as_arrays(y_true, scores) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    if y.shape[0] != s.shape[0]:
        raise ValueError("y_true and scores must share length")
    if y.shape[0] == 0:
        raise ValueError("cannot score an empty array")
    return y, s


def confusion_counts(y_true, scores, threshold: float) -> ConfusionCounts:
    y, s = _as_arrays(y_true, scores)
    pred = (s >= threshold).astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    return ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn)


def accuracy(y_true, scores, threshold: float) -> float:
    c = confusion_counts(y_true, scores, threshold)
    return (c.tp + c.tn) / c.total


def precision_at_threshold(y_true, scores, threshold: float) -> float:
    c = confusion_counts(y_true, scores, threshold)
    denom = c.tp + c.fp
    return c.tp / denom if denom else 0.0


def recall_at_threshold(y_true, scores, threshold: float) -> float:
    c = confusion_counts(y_true, scores, threshold)
    denom = c.tp + c.fn
    return c.tp / denom if denom else 0.0


def roc_auc(y_true, scores) -> float:
    y, s = _as_arrays(y_true, scores)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(roc_auc_score(y, s))


def average_precision(y_true, scores) -> float:
    y, s = _as_arrays(y_true, scores)
    if len(np.unique(y)) < 2:
        return float("nan")
    return float(average_precision_score(y, s))


def prevalence(y_true) -> float:
    y = np.asarray(y_true).astype(int)
    if y.shape[0] == 0:
        return 0.0
    return float(y.mean())
