from __future__ import annotations

import math
from typing import Mapping

import pandas as pd

from common.schema import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    UNKNOWN_CATEGORY,
    FeatureStats,
    expected_feature_order,
)


def _median(series: pd.Series) -> float:
    cleaned = series.dropna()
    if cleaned.empty:
        return 0.0
    return float(cleaned.median())


def fit_feature_stats(frame: pd.DataFrame, min_vocab_freq: int = 25) -> FeatureStats:
    numeric_medians = {name: _median(frame[name]) for name in NUMERIC_FEATURES}

    categorical_vocab = {}
    for name in CATEGORICAL_FEATURES:
        counts = frame[name].fillna(UNKNOWN_CATEGORY).value_counts()
        kept = [str(value) for value, freq in counts.items() if freq >= min_vocab_freq]
        if UNKNOWN_CATEGORY not in kept:
            kept.append(UNKNOWN_CATEGORY)
        categorical_vocab[name] = tuple(sorted(kept))

    return FeatureStats(
        numeric_medians=numeric_medians,
        categorical_vocab=categorical_vocab,
        feature_order=expected_feature_order(),
    )


def _impute_numeric(value, median: float) -> float:
    if value is None:
        return median
    if isinstance(value, float) and math.isnan(value):
        return median
    return float(value)


def _clip_amount(value: float) -> float:
    return max(0.0, min(value, 50_000.0))


def transform_row(row: Mapping, stats: FeatureStats) -> list[float]:
    encoded: list[float] = []
    for name in NUMERIC_FEATURES:
        median = stats.numeric_medians.get(name, 0.0)
        feature = _impute_numeric(row.get(name), median)
        if name == "amount":
            feature = _clip_amount(feature)
        encoded.append(feature)

    for name in CATEGORICAL_FEATURES:
        vocab = stats.categorical_vocab.get(name, (UNKNOWN_CATEGORY,))
        raw = row.get(name)
        token = str(raw) if raw is not None else UNKNOWN_CATEGORY
        if token not in vocab:
            token = UNKNOWN_CATEGORY
        encoded.append(float(vocab.index(token)))

    return encoded


def build_training_matrix(
    frame: pd.DataFrame, stats: FeatureStats
) -> list[list[float]]:
    return [transform_row(record, stats) for record in frame.to_dict("records")]
