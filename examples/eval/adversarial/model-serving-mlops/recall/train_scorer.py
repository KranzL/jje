import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import mlflow
import mlflow.sklearn

NUMERIC_FIELDS = [
    "amount",
    "account_age_days",
    "avg_ticket_30d",
    "velocity_1h",
    "distance_from_home_km",
]
CATEGORICAL_FIELDS = ["channel", "merchant_category", "device_class"]


def load_training_frame(path="transactions.parquet"):
    df = pd.read_parquet(path)
    df = df[df["label_finalized"]].copy()
    df["amount_to_avg_ratio"] = df["amount"] / (df["avg_ticket_30d"] + 1.0)
    return df


def build_pipeline():
    numeric = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC_FIELDS + ["amount_to_avg_ratio"],
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FIELDS,
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("pre", numeric),
            ("clf", HistGradientBoostingClassifier(learning_rate=0.05, max_iter=400)),
        ]
    )


def main():
    df = load_training_frame()
    feature_cols = NUMERIC_FIELDS + ["amount_to_avg_ratio"] + CATEGORICAL_FIELDS
    X = df[feature_cols]
    y = df["is_fraud"].astype(int)

    pipeline = build_pipeline()
    pipeline.fit(X, y)

    with mlflow.start_run():
        mlflow.sklearn.log_model(
            pipeline, artifact_path="model", registered_model_name="fraud_risk_scorer"
        )


if __name__ == "__main__":
    main()
