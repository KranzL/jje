from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Tuple

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

from common.schema import MODEL_NAME, FeatureStats
from training.build_features import build_training_matrix, fit_feature_stats


@dataclass(frozen=True)
class TrainingConfig:
    learning_rate: float = 0.05
    n_estimators: int = 300
    max_depth: int = 3
    random_state: int = 17
    test_size: float = 0.2


def _load_labeled_frame(path: str) -> Tuple[pd.DataFrame, pd.Series]:
    frame = pd.read_parquet(path)
    labels = frame.pop("is_fraud").astype(int)
    return frame, labels


def train(data_path: str, output_dir: str, config: TrainingConfig) -> str:
    frame, labels = _load_labeled_frame(data_path)

    stats = fit_feature_stats(frame)

    train_frame, holdout_frame, train_labels, holdout_labels = train_test_split(
        frame,
        labels,
        test_size=config.test_size,
        random_state=config.random_state,
        stratify=labels,
    )

    x_train = build_training_matrix(train_frame, stats)
    x_holdout = build_training_matrix(holdout_frame, stats)

    model = GradientBoostingClassifier(
        learning_rate=config.learning_rate,
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        random_state=config.random_state,
    )
    model.fit(x_train, train_labels)

    holdout_auc = float(model.score(x_holdout, holdout_labels))

    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, f"{MODEL_NAME}.joblib")
    stats_path = os.path.join(output_dir, "feature_stats.json")
    metrics_path = os.path.join(output_dir, "metrics.json")

    joblib.dump(model, model_path)
    with open(stats_path, "w", encoding="utf-8") as handle:
        json.dump(stats.to_dict(), handle, indent=2, sort_keys=True)
    with open(metrics_path, "w", encoding="utf-8") as handle:
        json.dump({"holdout_accuracy": holdout_auc}, handle, indent=2)

    return output_dir


def load_stats(output_dir: str) -> FeatureStats:
    with open(os.path.join(output_dir, "feature_stats.json"), encoding="utf-8") as fh:
        return FeatureStats.from_dict(json.load(fh))
