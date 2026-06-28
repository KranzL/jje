import numpy as np
import pandas as pd
import pytest

from churn.features import (
    add_engagement_trend,
    add_tenure_buckets,
    add_usage_ratios,
    engineer_features,
)
from churn.preprocessing import FrequencyEncoder, TargetMeanEncoder


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            "account_id": range(6),
            "region": ["north", "north", "south", "south", "west", "west"],
            "tenure_months": [1, 5, 13, 30, 50, 8],
            "monthly_charges": [20.0, 60.0, 80.0, 45.0, 90.0, 0.0],
            "total_charges": [20.0, 300.0, 1040.0, 1350.0, 4500.0, 0.0],
            "support_tickets": [0, 2, 1, 5, 0, 3],
            "logins_last_30d": [10, 0, 5, 8, 0, 12],
            "logins_prev_30d": [8, 4, 5, 4, 1, 6],
            "churned": [0, 1, 0, 1, 0, 1],
        }
    )


def test_tenure_buckets_are_assigned(frame):
    out = add_tenure_buckets(frame)
    assert out.loc[0, "tenure_bucket"] == "0-3m"
    assert out.loc[4, "tenure_bucket"] == "48m+"


def test_usage_ratios_handle_zero_charges(frame):
    out = add_usage_ratios(frame)
    assert out["support_per_charge"].notna().all()
    assert out.loc[5, "support_per_charge"] == 0.0


def test_engagement_trend_flags_dormant(frame):
    out = add_engagement_trend(frame)
    assert out.loc[1, "is_dormant"] == 1
    assert out.loc[0, "is_dormant"] == 0


def test_target_encoder_uses_only_fit_rows():
    X = pd.DataFrame({"plan_code": ["a", "a", "b", "b"]})
    y = np.array([1, 1, 0, 0])
    enc = TargetMeanEncoder(smoothing=0.0).fit(X, y)
    transformed = enc.transform(pd.DataFrame({"plan_code": ["a", "b", "c"]}))
    assert transformed[0, 0] == pytest.approx(1.0)
    assert transformed[1, 0] == pytest.approx(0.0)
    assert transformed[2, 0] == pytest.approx(0.5)


def test_frequency_encoder_relative_counts():
    X = pd.DataFrame({"device_type": ["ios", "ios", "android", "web"]})
    enc = FrequencyEncoder().fit(X)
    out = enc.transform(pd.DataFrame({"device_type": ["ios", "android", "unknown"]}))
    assert out[0, 0] == pytest.approx(0.5)
    assert out[1, 0] == pytest.approx(0.25)
    assert out[2, 0] == pytest.approx(0.0)


def test_engineer_features_adds_expected_columns(frame):
    out = engineer_features(frame)
    for col in ["tenure_bucket", "charges_per_tenure", "login_trend", "region_churn_rate"]:
        assert col in out.columns
