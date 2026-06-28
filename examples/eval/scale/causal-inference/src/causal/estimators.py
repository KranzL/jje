import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .covariates import AdjustmentSet, TREATMENT, OUTCOME_BINARY
from .propensity import (
    build_design_matrix,
    fit_propensity,
    propensity_scores,
    stabilized_ipw,
)


def fit_outcome_model(df: pd.DataFrame, adj: AdjustmentSet, treat_value: int) -> Pipeline:
    subset = df[df[TREATMENT] == treat_value]
    model = Pipeline(
        steps=[
            ("design", build_design_matrix(subset, adj)),
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ]
    )
    model.fit(subset[adj.all_columns()], subset[OUTCOME_BINARY])
    return model


def _predict_potential(model: Pipeline, df: pd.DataFrame, adj: AdjustmentSet) -> np.ndarray:
    return model.predict_proba(df[adj.all_columns()])[:, 1]


def aipw_ate(df: pd.DataFrame, adj: AdjustmentSet) -> dict:
    treatment = df[TREATMENT].to_numpy()
    y = df[OUTCOME_BINARY].to_numpy()

    ps_model = fit_propensity(df, adj)
    ps = propensity_scores(ps_model, df, adj)

    m1 = fit_outcome_model(df, adj, treat_value=1)
    m0 = fit_outcome_model(df, adj, treat_value=0)
    mu1 = _predict_potential(m1, df, adj)
    mu0 = _predict_potential(m0, df, adj)

    psi1 = mu1 + treatment * (y - mu1) / ps
    psi0 = mu0 + (1 - treatment) * (y - mu0) / (1 - ps)

    ate = float(np.mean(psi1 - psi0))
    se = float(np.std(psi1 - psi0, ddof=1) / np.sqrt(len(df)))
    return {
        "estimand": "ATE",
        "method": "aipw",
        "estimate": ate,
        "std_error": se,
        "ci_low": ate - 1.96 * se,
        "ci_high": ate + 1.96 * se,
    }


def ipw_ate(df: pd.DataFrame, adj: AdjustmentSet) -> dict:
    treatment = df[TREATMENT].to_numpy()
    y = df[OUTCOME_BINARY].to_numpy()

    ps_model = fit_propensity(df, adj)
    ps = propensity_scores(ps_model, df, adj)
    w = stabilized_ipw(treatment, ps)

    y1 = np.sum(w * treatment * y) / np.sum(w * treatment)
    y0 = np.sum(w * (1 - treatment) * y) / np.sum(w * (1 - treatment))
    ate = float(y1 - y0)
    return {
        "estimand": "ATE",
        "method": "ipw",
        "estimate": ate,
    }


def naive_difference(df: pd.DataFrame) -> dict:
    treated = df[df[TREATMENT] == 1][OUTCOME_BINARY].mean()
    control = df[df[TREATMENT] == 0][OUTCOME_BINARY].mean()
    return {
        "estimand": "association",
        "method": "unadjusted",
        "estimate": float(treated - control),
    }
