from __future__ import annotations

import pandas as pd

from common.schema import expected_feature_order
from serving.feature_assembler import assemble_features, order_matches
from training.build_features import fit_feature_stats, transform_row


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "amount": 120.0,
                "account_age_days": 800,
                "txn_count_7d": 4,
                "avg_ticket_30d": 60.0,
                "distance_from_home_km": 3.2,
                "merchant_category": "grocery",
                "device_type": "ios",
                "entry_mode": "chip",
            },
            {
                "amount": 9000.0,
                "account_age_days": 30,
                "txn_count_7d": 22,
                "avg_ticket_30d": 410.0,
                "distance_from_home_km": 540.0,
                "merchant_category": "electronics",
                "device_type": "android",
                "entry_mode": "ecommerce",
            },
        ]
        * 30
    )


def test_feature_order_is_stable():
    stats = fit_feature_stats(_sample_frame())
    assert tuple(stats.feature_order) == expected_feature_order()
    assert order_matches(stats)


def test_fully_populated_rows_match_between_train_and_serve():
    frame = _sample_frame()
    stats = fit_feature_stats(frame)

    for record in frame.to_dict("records"):
        offline = transform_row(record, stats)
        online = assemble_features(record, stats)
        assert offline == online
