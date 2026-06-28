from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_eval.metrics import (
    accuracy,
    average_precision,
    confusion_counts,
    precision_at_threshold,
    recall_at_threshold,
    roc_auc,
)
from fraud_eval.report import build_evaluation_report, promotion_gate
from fraud_eval.thresholds import select_operating_threshold


def _toy_frame(n: int = 2000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    is_fraud = (rng.random(n) < 0.01).astype(int)
    base = rng.random(n) * 0.4
    scores = np.clip(base + is_fraud * 0.5 + rng.normal(0, 0.05, n), 0, 1)
    amount = rng.gamma(2.0, 80.0, n)
    ts = pd.date_range("2026-01-01", periods=n, freq="min")
    return pd.DataFrame(
        {
            "authorized_at": ts,
            "is_fraud": is_fraud,
            "fraud_score": scores,
            "amount": amount,
        }
    )


def test_confusion_counts_partition() -> None:
    y = [0, 0, 1, 1]
    s = [0.1, 0.6, 0.4, 0.9]
    c = confusion_counts(y, s, threshold=0.5)
    assert c.total == 4
    assert c.tp == 1 and c.fp == 1 and c.tn == 1 and c.fn == 1


def test_precision_recall_consistency() -> None:
    y = [0, 1, 1, 1, 0]
    s = [0.2, 0.8, 0.7, 0.3, 0.9]
    assert precision_at_threshold(y, s, 0.5) == 2 / 3
    assert recall_at_threshold(y, s, 0.5) == 2 / 3


def test_roc_and_ap_agree_on_perfect_ranker() -> None:
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    assert roc_auc(y, s) == 1.0
    assert average_precision(y, s) == 1.0


def test_threshold_selected_on_validation_only() -> None:
    frame = _toy_frame()
    cut = int(len(frame) * 0.8)
    val = frame.iloc[:cut]
    op = select_operating_threshold(
        val["is_fraud"].to_numpy(),
        val["fraud_score"].to_numpy(),
        target_precision=0.3,
    )
    assert 0.0 <= op.threshold <= 1.0
    assert 0.0 <= op.recall <= 1.0


def test_report_and_gate_smoke() -> None:
    frame = _toy_frame()
    op = select_operating_threshold(
        frame["is_fraud"].to_numpy(),
        frame["fraud_score"].to_numpy(),
        target_precision=0.3,
    )
    report = build_evaluation_report(frame, op)
    assert report.n_examples == len(frame)
    assert report.positive_rate < 0.05
    promote, reasons = promotion_gate(report)
    assert isinstance(promote, bool)
    assert isinstance(reasons, list)
