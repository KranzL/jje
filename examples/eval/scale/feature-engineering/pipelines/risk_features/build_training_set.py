"""Assemble the offline training set for the application-default risk model.

Pipeline:
  1. Build the labeled spine (one row per matured application decision).
  2. Attach each feature group via a point-in-time correct as-of join.
  3. Produce an out-of-time split on the decision timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .feature_groups import account_balance, credit_bureau, transactions
from .spine import build_spine, sample_weight

LABEL_COLUMN = "defaulted"

NON_FEATURE_COLUMNS = [
    "application_id",
    "borrower_id",
    "decision_at",
    "label_at",
    "sample_weight",
]


@dataclass
class Sources:
    applications: pd.DataFrame
    outcomes: pd.DataFrame
    transactions: pd.DataFrame
    bureau: pd.DataFrame
    balances: pd.DataFrame
    income: pd.DataFrame


def _attach_stated_income(spine: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    income = income[["application_id", "stated_income"]].drop_duplicates("application_id")
    return spine.merge(income, on="application_id", how="left")


def build(sources: Sources, as_of_run_time: pd.Timestamp) -> pd.DataFrame:
    spine = build_spine(sources.applications, sources.outcomes, as_of_run_time)
    spine = _attach_stated_income(spine, sources.income)
    spine["sample_weight"] = sample_weight(spine)

    frame = transactions.attach(spine, sources.transactions)
    frame = credit_bureau.attach(frame, sources.bureau)
    frame = account_balance.attach(frame, sources.balances)

    return frame.sort_values("decision_at", kind="mergesort").reset_index(drop=True)


def out_of_time_split(
    frame: pd.DataFrame, cutoff: pd.Timestamp
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split so that every validation decision happens after every training decision."""

    train = frame.loc[frame["decision_at"] < cutoff].reset_index(drop=True)
    valid = frame.loc[frame["decision_at"] >= cutoff].reset_index(drop=True)
    return train, valid


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in NON_FEATURE_COLUMNS if c in frame.columns]
    drop.append(LABEL_COLUMN)
    return frame.drop(columns=[c for c in drop if c in frame.columns])
