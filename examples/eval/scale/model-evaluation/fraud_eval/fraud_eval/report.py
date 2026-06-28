from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .metrics import accuracy, prevalence, roc_auc
from .thresholds import OperatingPoint


@dataclass(frozen=True)
class EvaluationReport:
    n_examples: int
    positive_rate: float
    operating_threshold: float
    headline: dict[str, float]
    segment_auc: dict[str, float] = field(default_factory=dict)

    def as_row(self) -> dict[str, float]:
        row = {
            "n_examples": float(self.n_examples),
            "positive_rate": self.positive_rate,
            "operating_threshold": self.operating_threshold,
        }
        row.update({f"headline_{k}": v for k, v in self.headline.items()})
        return row


def _segment_auc(
    y_true: np.ndarray,
    scores: np.ndarray,
    amount: np.ndarray,
    edges: tuple[float, ...] = (0.0, 50.0, 250.0, 1000.0, float("inf")),
) -> dict[str, float]:
    out: dict[str, float] = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (amount >= lo) & (amount < hi)
        if mask.sum() == 0:
            continue
        seg_y = y_true[mask]
        if len(np.unique(seg_y)) < 2:
            continue
        label = f"[{lo:g},{hi:g})"
        out[label] = roc_auc(seg_y, scores[mask])
    return out


def build_evaluation_report(
    frame: pd.DataFrame,
    operating_point: OperatingPoint,
    label_col: str = "is_fraud",
    score_col: str = "fraud_score",
    amount_col: str = "amount",
) -> EvaluationReport:
    y = frame[label_col].to_numpy().astype(int)
    scores = frame[score_col].to_numpy(dtype=float)
    threshold = operating_point.threshold

    headline = {
        "accuracy": accuracy(y, scores, threshold),
        "roc_auc": roc_auc(y, scores),
    }

    segment = {}
    if amount_col in frame.columns:
        segment = _segment_auc(y, scores, frame[amount_col].to_numpy(dtype=float))

    return EvaluationReport(
        n_examples=int(len(y)),
        positive_rate=prevalence(y),
        operating_threshold=threshold,
        headline=headline,
        segment_auc=segment,
    )


def promotion_gate(
    report: EvaluationReport,
    min_accuracy: float = 0.985,
    min_auc: float = 0.90,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if report.headline["accuracy"] < min_accuracy:
        reasons.append(
            f"accuracy {report.headline['accuracy']:.4f} < floor {min_accuracy:.4f}"
        )
    if report.headline["roc_auc"] < min_auc:
        reasons.append(
            f"roc_auc {report.headline['roc_auc']:.4f} < floor {min_auc:.4f}"
        )
    return (len(reasons) == 0, reasons)
