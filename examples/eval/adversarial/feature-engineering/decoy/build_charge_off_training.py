import pandas as pd

FEATURE_COLUMNS = [
    "utilization_ratio",
    "num_open_tradelines",
    "months_since_last_delinquency",
    "rolling_inquiry_count_90d",
]


def load_credit_metrics(path: str) -> pd.DataFrame:
    metrics = pd.read_parquet(path)
    metrics["metric_ts"] = pd.to_datetime(metrics["metric_ts"], utc=True)
    return metrics.sort_values("metric_ts")


def build_entity_frame(
    applications_path: str,
    outcomes_path: str,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> pd.DataFrame:
    apps = pd.read_parquet(applications_path)
    apps["decision_at"] = pd.to_datetime(apps["decision_at"], utc=True)
    apps = apps[(apps["decision_at"] >= window_start) & (apps["decision_at"] < window_end)]

    outcomes = pd.read_parquet(outcomes_path)
    outcomes["outcome_observed_at"] = pd.to_datetime(outcomes["outcome_observed_at"], utc=True)

    entity = apps.merge(outcomes, on="loan_id", how="inner")
    entity["is_charge_off"] = (entity["final_status"] == "charge_off").astype(int)
    entity["label_horizon_days"] = (
        entity["outcome_observed_at"] - entity["decision_at"]
    ).dt.days
    entity["event_timestamp"] = entity["decision_at"]
    return entity.sort_values("event_timestamp")


def attach_point_in_time_features(
    entity: pd.DataFrame, metrics: pd.DataFrame
) -> pd.DataFrame:
    joined = pd.merge_asof(
        entity,
        metrics,
        left_on="event_timestamp",
        right_on="metric_ts",
        by="borrower_id",
        direction="backward",
        allow_exact_matches=False,
        tolerance=pd.Timedelta(days=120),
    )
    keep = [
        "loan_id",
        "borrower_id",
        "decision_at",
        "outcome_observed_at",
        "label_horizon_days",
        "is_charge_off",
        *FEATURE_COLUMNS,
    ]
    return joined[keep]


def main() -> None:
    metrics = load_credit_metrics("s3://feature-store/credit_metrics/")
    entity = build_entity_frame(
        "s3://lending/applications/",
        "s3://lending/outcomes/",
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2025-01-01", tz="UTC"),
    )
    training = attach_point_in_time_features(entity, metrics)
    training.to_parquet("s3://training/charge_off_v3/")


if __name__ == "__main__":
    main()
