import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .covariates import (
    AdjustmentSet,
    TREATMENT,
    OUTCOME_BINARY,
    MEDIATOR,
    BASELINE_NUMERIC,
)


def _baseline_only(adj: AdjustmentSet) -> list:
    return [c for c in adj.binary if c != MEDIATOR] + adj.numeric + adj.categorical


def estimate_natural_effects(df: pd.DataFrame, adj: AdjustmentSet) -> dict:
    confounders = [c for c in _baseline_only(adj) if c in df.columns]
    feat_med = confounders + [TREATMENT]
    feat_out = confounders + [TREATMENT, MEDIATOR]

    med_model = LogisticRegression(max_iter=1000)
    med_model.fit(_numeric_frame(df, feat_med), df[MEDIATOR])

    out_model = LogisticRegression(max_iter=1000)
    out_model.fit(_numeric_frame(df, feat_out), df[OUTCOME_BINARY])

    nde = _natural_direct(df, med_model, out_model, confounders)
    nie = _natural_indirect(df, med_model, out_model, confounders)
    return {
        "estimand": "mediation",
        "mediator": MEDIATOR,
        "natural_direct_effect": nde,
        "natural_indirect_effect": nie,
        "total_effect": nde + nie,
    }


def _numeric_frame(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    num = [c for c in cols if c in BASELINE_NUMERIC or df[c].dtype != object]
    return df[num].astype(float)


def _counterfactual(df, med_model, out_model, confounders, t_out, t_med):
    base = df.copy()
    base[TREATMENT] = t_med
    feat_med = [c for c in confounders if df[c].dtype != object] + [TREATMENT]
    p_m = med_model.predict_proba(base[feat_med].astype(float))[:, 1]

    total = np.zeros(len(df))
    for m_val, p in [(1, p_m), (0, 1 - p_m)]:
        scen = df.copy()
        scen[TREATMENT] = t_out
        scen[MEDIATOR] = m_val
        feat_out = [c for c in confounders if df[c].dtype != object] + [TREATMENT, MEDIATOR]
        y_hat = out_model.predict_proba(scen[feat_out].astype(float))[:, 1]
        total += p * y_hat
    return float(total.mean())


def _natural_direct(df, med_model, out_model, confounders):
    y10 = _counterfactual(df, med_model, out_model, confounders, t_out=1, t_med=0)
    y00 = _counterfactual(df, med_model, out_model, confounders, t_out=0, t_med=0)
    return y10 - y00


def _natural_indirect(df, med_model, out_model, confounders):
    y11 = _counterfactual(df, med_model, out_model, confounders, t_out=1, t_med=1)
    y10 = _counterfactual(df, med_model, out_model, confounders, t_out=1, t_med=0)
    return y11 - y10
