from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .report import build_evaluation_report, promotion_gate
from .thresholds import select_operating_threshold


def _split_by_time(frame: pd.DataFrame, ts_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values(ts_col, kind="mergesort").reset_index(drop=True)
    cut = int(len(ordered) * 0.8)
    val = ordered.iloc[:cut]
    test = ordered.iloc[cut:]
    return val, test


def run(
    scored_path: Path,
    target_precision: float = 0.5,
    ts_col: str = "authorized_at",
) -> dict:
    frame = pd.read_parquet(scored_path)
    val, test = _split_by_time(frame, ts_col)

    op = select_operating_threshold(
        val["is_fraud"].to_numpy().astype(int),
        val["fraud_score"].to_numpy(dtype=float),
        target_precision=target_precision,
    )

    report = build_evaluation_report(test, op)
    promote, reasons = promotion_gate(report)

    return {
        "operating_point": {
            "threshold": op.threshold,
            "precision": op.precision,
            "recall": op.recall,
        },
        "report": report.as_row(),
        "segment_auc": report.segment_auc,
        "promote": promote,
        "blocking_reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the fraud scoring model")
    parser.add_argument("scored_path", type=Path)
    parser.add_argument("--target-precision", type=float, default=0.5)
    args = parser.parse_args()

    result = run(args.scored_path, target_precision=args.target_precision)
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    main()
