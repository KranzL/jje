"""Training entrypoint for the churn propensity model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from .features import engineer_features
from .pipeline import build_pipeline, cross_validate_model

LABEL = "churned"
ID_COLS = ["account_id", "region"]


def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df.dropna(subset=[LABEL])
    df[LABEL] = df[LABEL].astype(int)
    return df


def split_features_labels(df: pd.DataFrame):
    y = df[LABEL].to_numpy()
    X = df.drop(columns=[LABEL] + [c for c in ID_COLS if c in df.columns])
    return X, y


def run(data_path: str, out_path: str, test_size: float = 0.2, seed: int = 7) -> dict:
    raw = load_dataset(data_path)

    engineered = engineer_features(raw, label_col=LABEL)

    train_df, test_df = train_test_split(
        engineered,
        test_size=test_size,
        stratify=engineered[LABEL],
        random_state=seed,
    )

    X_train, y_train = split_features_labels(train_df)
    X_test, y_test = split_features_labels(test_df)

    cv_report = cross_validate_model(X_train, y_train, random_state=seed)

    pipeline = build_pipeline(random_state=seed)
    pipeline.fit(X_train, y_train)

    test_proba = pipeline.predict_proba(X_test)[:, 1]
    holdout_auc = float(roc_auc_score(y_test, test_proba))

    report = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "positive_rate": float(np.mean(y_train)),
        "cv": cv_report,
        "holdout_auc": holdout_auc,
    }

    Path(out_path).write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train churn propensity model")
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", default="metrics.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    report = run(args.data, args.out, test_size=args.test_size, seed=args.seed)
    print(json.dumps(report["cv"], indent=2))


if __name__ == "__main__":
    main()
