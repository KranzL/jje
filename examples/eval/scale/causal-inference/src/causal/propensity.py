import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from .covariates import AdjustmentSet, TREATMENT


def build_design_matrix(df: pd.DataFrame, adj: AdjustmentSet) -> ColumnTransformer:
    transformer = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), adj.categorical),
            ("num", StandardScaler(), adj.numeric),
            ("bin", "passthrough", adj.binary),
        ],
        remainder="drop",
    )
    return transformer


def fit_propensity(df: pd.DataFrame, adj: AdjustmentSet) -> Pipeline:
    model = Pipeline(
        steps=[
            ("design", build_design_matrix(df, adj)),
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ]
    )
    model.fit(df[adj.all_columns()], df[TREATMENT])
    return model


def propensity_scores(model: Pipeline, df: pd.DataFrame, adj: AdjustmentSet) -> np.ndarray:
    p = model.predict_proba(df[adj.all_columns()])[:, 1]
    return np.clip(p, 1e-3, 1 - 1e-3)


def stabilized_ipw(treatment: np.ndarray, ps: np.ndarray) -> np.ndarray:
    p_treat = treatment.mean()
    w = np.where(
        treatment == 1,
        p_treat / ps,
        (1 - p_treat) / (1 - ps),
    )
    return w


def check_overlap(ps: np.ndarray, treatment: np.ndarray, eps: float = 0.01) -> dict:
    treated = ps[treatment == 1]
    control = ps[treatment == 0]
    return {
        "treated_min": float(treated.min()),
        "treated_max": float(treated.max()),
        "control_min": float(control.min()),
        "control_max": float(control.max()),
        "share_extreme": float(np.mean((ps < eps) | (ps > 1 - eps))),
    }
