import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def load_applications(path="applications.parquet"):
    df = pd.read_parquet(path)
    df = df[df["application_status"].isin(["funded", "declined"])].copy()
    df["defaulted"] = (df["loan_outcome"] == "charged_off").astype(int)
    df["dti"] = df["monthly_debt"] / df["monthly_income"].replace(0, np.nan)
    df["credit_age_years"] = df["credit_age_months"] / 12.0
    return df.dropna(subset=["dti", "annual_income", "credit_age_years"])


class SegmentRateEncoder(BaseEstimator, TransformerMixin):
    def __init__(self, key="employer_segment", smoothing=20.0):
        self.key = key
        self.smoothing = smoothing

    def fit(self, X, y):
        df = X[[self.key]].copy()
        df["_t"] = np.asarray(y)
        stats = df.groupby(self.key, observed=True)["_t"].agg(["mean", "count"])
        self.prior_ = float(df["_t"].mean())
        w = stats["count"] / (stats["count"] + self.smoothing)
        self.mapping_ = (w * stats["mean"] + (1.0 - w) * self.prior_).to_dict()
        return self

    def transform(self, X):
        col = X[self.key].map(self.mapping_).fillna(self.prior_)
        return col.to_frame("segment_default_rate").to_numpy()


def build_design_matrix(df):
    numeric = ["dti", "annual_income", "credit_age_years"]
    categorical = ["home_ownership", "loan_purpose"]
    X = df[numeric + categorical + ["employer_segment"]].copy()
    y = df["defaulted"].astype(int)
    return X, y, numeric, categorical


def make_estimator(numeric, categorical):
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("seg", SegmentRateEncoder(), ["employer_segment"]),
        ]
    )
    return Pipeline(
        steps=[
            ("pre", pre),
            ("clf", LogisticRegression(max_iter=1000, C=0.5)),
        ]
    )


def main():
    df = load_applications()
    X, y, numeric, categorical = build_design_matrix(df)

    estimator = make_estimator(numeric, categorical)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    scores = cross_val_score(estimator, X, y, cv=cv, scoring="roc_auc")

    print(f"mean roc_auc: {scores.mean():.4f} (+/- {scores.std():.4f})")
    estimator.fit(X, y)
    return estimator


if __name__ == "__main__":
    main()
