"""Account-balance feature group.

End-of-day ledger balances for the borrower's deposit accounts, stamped with the
ledger close timestamp ``balance_at``. We carry forward the last observed balance
and a few derived ratios. Balances are sparse for thin-file borrowers, so a null
balance is mapped to a dedicated indicator rather than zero.
"""

from __future__ import annotations

import pandas as pd

from ..asof import AsOfSpec, as_of_join

SPEC = AsOfSpec(entity_key="borrower_id", event_time="balance_at")

FEATURE_COLUMNS = [
    "deposit_balance",
    "min_balance_30d",
    "avg_balance_30d",
    "days_negative_30d",
]


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    feats = raw[["borrower_id", "balance_at", *FEATURE_COLUMNS]].copy()
    feats["balance_at"] = pd.to_datetime(feats["balance_at"])
    return feats


def attach(spine: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Attach the most recent ledger balance for the borrower."""

    feats = _prepare(raw)
    out = as_of_join(spine, feats, anchor_col="label_at", spec=SPEC)

    out["balance_missing"] = out["deposit_balance"].isna().astype(int)
    out["deposit_balance"] = out["deposit_balance"].fillna(0.0)
    out["balance_to_income"] = out["avg_balance_30d"] / out.get("stated_income", pd.NA)
    return out
