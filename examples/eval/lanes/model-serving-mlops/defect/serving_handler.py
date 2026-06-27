import mlflow
import numpy as np
import pandas as pd
import xgboost as xgb

FEATURES = ["amount", "account_age_days", "txn_count_30d", "merchant_risk"]


def train(raw: pd.DataFrame) -> xgb.XGBClassifier:
    X = raw[FEATURES].astype(np.float32)
    y = raw["is_fraud"].astype(int)
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        missing=np.nan,
    )
    model.fit(X, y)
    return model


class FraudScorer:
    def __init__(self, model_uri: str) -> None:
        self.model = mlflow.pyfunc.load_model(model_uri)

    def preprocess(self, payload: dict) -> pd.DataFrame:
        row = {f: payload.get(f) for f in FEATURES}
        df = pd.DataFrame([row], columns=FEATURES)
        df = df.fillna(0.0).astype(np.float32)
        return df

    def predict(self, payload: dict) -> float:
        df = self.preprocess(payload)
        score = self.model.predict(df)
        return float(score[0])
