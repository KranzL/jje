import logging

import pandas as pd
from scipy.stats import ks_2samp

logger = logging.getLogger("drift_monitor")

CONTINUOUS_FEATURES = ["txn_amount", "account_age_days", "merchant_risk_score"]
P_VALUE_THRESHOLD = 0.05


def load_reference():
    return pd.read_parquet("s3://feature-store/fraud_model/reference_train_2026q1.parquet")


def load_production_window():
    return pd.read_parquet("s3://prediction-logs/fraud_model/serving_inputs_today.parquet")


def check_feature_drift(reference, production, feature):
    ref_values = reference[feature].dropna()
    prod_values = production[feature].dropna()

    statistic, p_value = ks_2samp(ref_values, prod_values)

    drifted = p_value < P_VALUE_THRESHOLD
    return {
        "feature": feature,
        "ks_statistic": float(statistic),
        "p_value": float(p_value),
        "n_reference": int(len(ref_values)),
        "n_production": int(len(prod_values)),
        "drifted": bool(drifted),
    }


def route_alert(result):
    logger.warning(
        "DRIFT severity=high feature=%s p_value=%.6f runbook=runbooks/fraud-drift.md",
        result["feature"],
        result["p_value"],
    )


def run():
    reference = load_reference()
    production = load_production_window()

    results = []
    for feature in CONTINUOUS_FEATURES:
        result = check_feature_drift(reference, production, feature)
        results.append(result)
        if result["drifted"]:
            route_alert(result)

    return results


if __name__ == "__main__":
    run()
