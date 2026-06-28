"""Credit-bureau feature group.

Bureau pulls arrive irregularly. Each pull is stamped with ``pulled_at``, the
moment the report was retrieved, which is when its contents first became
observable. A bureau pull can be stale by up to 35 days at decision time before
we treat it as missing, so the as-of join carries a tolerance.
"""

from __future__ import annotations

import pandas as pd

from ..asof import AsOfSpec, as_of_join

SPEC = AsOfSpec(
    entity_key="borrower_id",
    event_time="pulled_at",
    tolerance=pd.Timedelta(days=35),
)

FEATURE_COLUMNS = [
    "fico_score",
    "revolving_utilization",
    "inquiries_6m",
    "open_tradelines",
]


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    feats = raw[["borrower_id", "pulled_at", *FEATURE_COLUMNS]].copy()
    feats["pulled_at"] = pd.to_datetime(feats["pulled_at"])
    return feats.dropna(subset=["pulled_at"])


def attach(spine: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Attach the freshest bureau pull retrievable at decision time."""

    feats = _prepare(raw)
    out = as_of_join(spine, feats, anchor_col="decision_at", spec=SPEC)
    out["fico_missing"] = out["fico_score"].isna().astype(int)
    return out
