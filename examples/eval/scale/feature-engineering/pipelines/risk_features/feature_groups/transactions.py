"""Transaction-velocity feature group.

Source is a rolling daily aggregate of the borrower's checking-account
transactions. Each row is the borrower's state as of the close of one day, so
the event-log timestamp is ``snapshot_at``.
"""

from __future__ import annotations

import pandas as pd

from ..asof import AsOfSpec, as_of_join

SPEC = AsOfSpec(entity_key="borrower_id", event_time="snapshot_at")

FEATURE_COLUMNS = [
    "txn_count_30d",
    "txn_amount_30d",
    "txn_count_7d",
    "nsf_count_90d",
]


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    feats = raw[["borrower_id", "snapshot_at", *FEATURE_COLUMNS]].copy()
    feats["snapshot_at"] = pd.to_datetime(feats["snapshot_at"])
    return feats


def attach(spine: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Attach velocity features observable at decision time."""

    feats = _prepare(raw)
    out = as_of_join(spine, feats, anchor_col="decision_at", spec=SPEC)

    out["txn_amount_30d"] = out["txn_amount_30d"].fillna(0.0)
    out["txn_count_30d"] = out["txn_count_30d"].fillna(0).astype("Int64")
    return out
