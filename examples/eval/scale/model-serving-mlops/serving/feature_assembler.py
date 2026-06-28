from __future__ import annotations

from typing import Mapping

from common.schema import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    UNKNOWN_CATEGORY,
    FeatureStats,
)

_DEFAULT_NUMERIC = 0.0
_AMOUNT_LOWER = 0.0
_AMOUNT_UPPER = 50_000.0


def _coerce_numeric(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clip_amount(value: float) -> float:
    return max(_AMOUNT_LOWER, min(value, _AMOUNT_UPPER))


def _encode_categorical(name: str, value, stats: FeatureStats) -> float:
    vocab = stats.categorical_vocab.get(name, (UNKNOWN_CATEGORY,))
    token = str(value) if value is not None else UNKNOWN_CATEGORY
    if token not in vocab:
        token = UNKNOWN_CATEGORY
    return float(vocab.index(token))


def assemble_features(payload: Mapping, stats: FeatureStats) -> list[float]:
    vector: list[float] = []

    for name in NUMERIC_FEATURES:
        coerced = _coerce_numeric(payload.get(name))
        feature = _DEFAULT_NUMERIC if coerced is None else coerced
        if name == "amount":
            feature = _clip_amount(feature)
        vector.append(feature)

    for name in CATEGORICAL_FEATURES:
        vector.append(_encode_categorical(name, payload.get(name), stats))

    return vector


def order_matches(stats: FeatureStats) -> bool:
    expected = tuple(NUMERIC_FEATURES) + tuple(CATEGORICAL_FEATURES)
    return tuple(stats.feature_order) == expected
