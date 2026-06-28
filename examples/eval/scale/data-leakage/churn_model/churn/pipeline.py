"""Model pipeline assembly and cross-validation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .preprocessing import FrequencyEncoder, TargetMeanEncoder

NUMERIC_FEATURES = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "charges_per_tenure",
    "support_per_charge",
    "login_trend",
    "region_churn_rate",
]

LOW_CARD_CATEGORICAL = ["contract_type", "payment_method", "tenure_bucket"]
HIGH_CARD_CATEGORICAL = ["plan_code", "acquisition_channel"]
FREQUENCY_CATEGORICAL = ["device_type"]


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    low_card = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    high_card = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("target", TargetMeanEncoder(smoothing=20.0)),
        ]
    )
    frequency = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("freq", FrequencyEncoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("low", low_card, LOW_CARD_CATEGORICAL),
            ("high", high_card, HIGH_CARD_CATEGORICAL),
            ("freq", frequency, FREQUENCY_CATEGORICAL),
        ],
        remainder="drop",
    )


def build_pipeline(random_state: int = 7) -> Pipeline:
    return Pipeline(
        steps=[
            ("features", build_preprocessor()),
            (
                "model",
                GradientBoostingClassifier(
                    n_estimators=300,
                    max_depth=3,
                    learning_rate=0.05,
                    subsample=0.9,
                    random_state=random_state,
                ),
            ),
        ]
    )


def cross_validate_model(
    X: pd.DataFrame,
    y: np.ndarray,
    n_splits: int = 5,
    random_state: int = 7,
) -> dict:
    pipeline = build_pipeline(random_state=random_state)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc")
    return {
        "mean_auc": float(scores.mean()),
        "std_auc": float(scores.std()),
        "fold_auc": scores.tolist(),
    }
