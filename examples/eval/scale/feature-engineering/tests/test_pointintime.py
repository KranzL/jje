import pandas as pd

from pipelines.risk_features.asof import AsOfSpec, as_of_join, assert_no_future_rows
from pipelines.risk_features.feature_groups import credit_bureau, transactions


def _spine():
    return pd.DataFrame(
        {
            "application_id": [1, 2],
            "borrower_id": ["b1", "b1"],
            "decision_at": pd.to_datetime(["2024-03-01", "2024-06-01"]),
            "label_at": pd.to_datetime(["2024-05-30", "2024-08-30"]),
        }
    )


def test_backward_join_excludes_future_events():
    spine = _spine()
    feats = pd.DataFrame(
        {
            "borrower_id": ["b1", "b1", "b1"],
            "snapshot_at": pd.to_datetime(["2024-02-20", "2024-04-15", "2024-05-25"]),
            "txn_count_30d": [3, 9, 14],
            "txn_amount_30d": [100.0, 400.0, 700.0],
            "txn_count_7d": [1, 2, 4],
            "nsf_count_90d": [0, 1, 1],
        }
    )
    spec = AsOfSpec(entity_key="borrower_id", event_time="snapshot_at")
    joined = as_of_join(spine, feats, anchor_col="decision_at", spec=spec)
    assert joined.loc[joined["application_id"] == 1, "txn_count_30d"].iloc[0] == 3


def test_transactions_group_is_point_in_time_safe():
    spine = _spine()
    raw = pd.DataFrame(
        {
            "borrower_id": ["b1", "b1"],
            "snapshot_at": pd.to_datetime(["2024-02-01", "2024-07-01"]),
            "txn_count_30d": [5, 50],
            "txn_amount_30d": [250.0, 2500.0],
            "txn_count_7d": [1, 10],
            "nsf_count_90d": [0, 3],
        }
    )
    out = transactions.attach(spine, raw)
    assert out.loc[out["application_id"] == 1, "txn_count_30d"].iloc[0] == 5


def test_bureau_tolerance_drops_stale_pull():
    spine = _spine()
    raw = pd.DataFrame(
        {
            "borrower_id": ["b1"],
            "pulled_at": pd.to_datetime(["2023-12-01"]),
            "fico_score": [710],
            "revolving_utilization": [0.3],
            "inquiries_6m": [2],
            "open_tradelines": [6],
        }
    )
    out = credit_bureau.attach(spine, raw)
    assert out["fico_missing"].iloc[0] == 1
