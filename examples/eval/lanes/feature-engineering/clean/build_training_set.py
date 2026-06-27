import pandas as pd


def load_account_features(path: str) -> pd.DataFrame:
    features = pd.read_parquet(path)
    features["event_timestamp"] = pd.to_datetime(features["event_timestamp"], utc=True)
    return features.sort_values("event_timestamp")


def load_label_spine(path: str) -> pd.DataFrame:
    spine = pd.read_parquet(path)
    spine["decision_timestamp"] = pd.to_datetime(spine["decision_timestamp"], utc=True)
    return spine.sort_values("decision_timestamp")


def build_training_set(features: pd.DataFrame, spine: pd.DataFrame) -> pd.DataFrame:
    training = pd.merge_asof(
        spine,
        features,
        left_on="decision_timestamp",
        right_on="event_timestamp",
        by="account_id",
        direction="backward",
    )
    return training[
        [
            "account_id",
            "decision_timestamp",
            "rolling_spend_30d",
            "active_disputes",
            "is_chargeback",
        ]
    ]


def main() -> None:
    features = load_account_features("s3://feature-store/account_features/")
    spine = load_label_spine("s3://labels/chargeback_spine/")
    training = build_training_set(features, spine)
    training.to_parquet("s3://training/chargeback_v1/")


if __name__ == "__main__":
    main()
