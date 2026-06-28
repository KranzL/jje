"""Label spine construction for the application-default risk model.

The model scores a loan application *at the moment of decision*. The outcome
(default within the performance window) is only known later, once the window
closes. The spine therefore carries two distinct timestamps per row:

  * ``decision_at`` - when the application was scored. This is the only time the
    model is allowed to "see" the world from. All features anchor here.
  * ``label_at`` - when the outcome became known (decision time plus the
    performance window). Used purely to resolve the label and to censor rows
    whose window has not closed yet.
"""

from __future__ import annotations

import pandas as pd

PERFORMANCE_WINDOW = pd.Timedelta(days=90)


def build_spine(
    applications: pd.DataFrame,
    outcomes: pd.DataFrame,
    as_of_run_time: pd.Timestamp,
) -> pd.DataFrame:
    """Assemble one labeled row per scored application.

    ``applications`` has ``application_id``, ``borrower_id`` and ``decision_at``.
    ``outcomes`` has ``application_id`` and ``defaulted`` plus ``resolved_at``.
    """

    spine = applications[["application_id", "borrower_id", "decision_at"]].copy()
    spine["label_at"] = spine["decision_at"] + PERFORMANCE_WINDOW

    spine = spine.merge(
        outcomes[["application_id", "defaulted"]],
        on="application_id",
        how="left",
    )
    spine["defaulted"] = spine["defaulted"].fillna(0).astype(int)

    matured = spine["label_at"] <= as_of_run_time
    spine = spine.loc[matured].reset_index(drop=True)

    return spine.sort_values("decision_at", kind="mergesort").reset_index(drop=True)


def sample_weight(spine: pd.DataFrame, half_life_days: float = 180.0) -> pd.Series:
    """Recency weighting so stale decisions count for less at fit time."""

    age = (spine["decision_at"].max() - spine["decision_at"]).dt.total_seconds()
    age_days = age / 86400.0
    decay = 0.5 ** (age_days / half_life_days)
    return decay.rename("sample_weight")
