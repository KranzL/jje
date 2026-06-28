from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


NUMERIC_FEATURES: Sequence[str] = (
    "amount",
    "account_age_days",
    "txn_count_7d",
    "avg_ticket_30d",
    "distance_from_home_km",
)

CATEGORICAL_FEATURES: Sequence[str] = (
    "merchant_category",
    "device_type",
    "entry_mode",
)

UNKNOWN_CATEGORY = "__unknown__"

MODEL_NAME = "card_fraud_scorer"


@dataclass(frozen=True)
class FeatureStats:
    numeric_medians: Mapping[str, float] = field(default_factory=dict)
    categorical_vocab: Mapping[str, Sequence[str]] = field(default_factory=dict)
    feature_order: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "numeric_medians": dict(self.numeric_medians),
            "categorical_vocab": {k: list(v) for k, v in self.categorical_vocab.items()},
            "feature_order": list(self.feature_order),
        }

    @classmethod
    def from_dict(cls, payload: Mapping) -> "FeatureStats":
        return cls(
            numeric_medians=dict(payload.get("numeric_medians", {})),
            categorical_vocab={
                k: tuple(v) for k, v in payload.get("categorical_vocab", {}).items()
            },
            feature_order=tuple(payload.get("feature_order", ())),
        )


def expected_feature_order() -> Sequence[str]:
    return tuple(NUMERIC_FEATURES) + tuple(CATEGORICAL_FEATURES)
