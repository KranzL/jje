import numpy as np
import pandas as pd
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


def attach_segment_baselines(df):
    seg = df.groupby("employer_segment", observed=True)["defaulted"].mean()
    seg.name = "segment_default_rate"
    out = df.join(seg, on="employer_segment")
    overall = df["defaulted"].mean()
    out["segment_default_rate"] = out["segment_default_rate"].fillna(overall)
    return out


def build_design_matrix(df):
    numeric = ["dti", "annual_income", "credit_age_years", "segment_default_rate"]
    categorical = ["home_ownership", "loan_purpose"]
    X = df[numeric + categorical].copy()
    y = df["defaulted"].astype(int)
    return X, y, numeric, categorical


def make_estimator(numeric, categorical):
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
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
    df = attach_segment_baselines(df)
    X, y, numeric, categorical = build_design_matrix(df)

    estimator = make_estimator(numeric, categorical)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    scores = cross_val_score(estimator, X, y, cv=cv, scoring="roc_auc")

    print(f"mean roc_auc: {scores.mean():.4f} (+/- {scores.std():.4f})")
    estimator.fit(X, y)
    return estimator


if __name__ == "__main__":
    main()
