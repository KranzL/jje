import logging

import pandas as pd
from scipy.stats import ks_2samp

logger = logging.getLogger("drift_monitor")

CONTINUOUS_FEATURES = ["txn_amount", "account_age_days", "merchant_risk_score"]
KS_STATISTIC_WARN = 0.1
KS_STATISTIC_ACTION = 0.2
MIN_SAMPLES = 1000


def load_reference():
    return pd.read_parquet("s3://feature-store/fraud_model/reference_train_2026q1.parquet")


def load_production_window():
    return pd.read_parquet("s3://prediction-logs/fraud_model/serving_inputs_today.parquet")


def check_feature_drift(reference, production, feature):
    ref_values = reference[feature].dropna()
    prod_values = production[feature].dropna()

    if len(ref_values) < MIN_SAMPLES or len(prod_values) < MIN_SAMPLES:
        return {
            "feature": feature,
            "ks_statistic": None,
            "n_reference": int(len(ref_values)),
            "n_production": int(len(prod_values)),
            "severity": "skipped_insufficient_sample",
        }

    statistic, _p_value = ks_2samp(ref_values, prod_values)

    if statistic >= KS_STATISTIC_ACTION:
        severity = "action"
    elif statistic >= KS_STATISTIC_WARN:
        severity = "warn"
    else:
        severity = "ok"

    return {
        "feature": feature,
        "ks_statistic": float(statistic),
        "n_reference": int(len(ref_values)),
        "n_production": int(len(prod_values)),
        "severity": severity,
    }


def route_alert(result):
    logger.warning(
        "DRIFT severity=%s feature=%s ks_statistic=%.4f runbook=runbooks/fraud-drift.md",
        result["severity"],
        result["feature"],
        result["ks_statistic"],
    )


def run():
    reference = load_reference()
    production = load_production_window()

    results = []
    for feature in CONTINUOUS_FEATURES:
        result = check_feature_drift(reference, production, feature)
        results.append(result)
        if result["severity"] in ("warn", "action"):
            route_alert(result)

    return results


if __name__ == "__main__":
    run()
