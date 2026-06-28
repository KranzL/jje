"""Point-in-time correct as-of join primitives for offline feature assembly.

Every feature group is materialized as an event-log keyed by ``entity_id`` and an
observation timestamp. To build a training row we must look up, for each entity,
the most recent feature value that was *already observable* at the row's anchor
time. ``pandas.merge_asof`` with ``direction="backward"`` gives exactly this when
both frames are sorted by the join timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AsOfSpec:
    entity_key: str
    event_time: str
    tolerance: pd.Timedelta | None = None


def as_of_join(
    spine: pd.DataFrame,
    features: pd.DataFrame,
    anchor_col: str,
    spec: AsOfSpec,
) -> pd.DataFrame:
    """Attach the last feature row observable at ``spine[anchor_col]``.

    ``spine`` carries the entity and the anchor timestamp; ``features`` is the
    feature event-log. The join is strictly backward-looking: a feature row only
    matches when ``features[spec.event_time] <= spine[anchor_col]``.
    """

    if anchor_col not in spine.columns:
        raise KeyError(f"anchor column {anchor_col!r} missing from spine")
    if spec.event_time not in features.columns:
        raise KeyError(f"event-time column {spec.event_time!r} missing from features")

    left = spine.sort_values(anchor_col, kind="mergesort")
    right = features.sort_values(spec.event_time, kind="mergesort")

    joined = pd.merge_asof(
        left,
        right,
        left_on=anchor_col,
        right_on=spec.event_time,
        by=spec.entity_key,
        direction="backward",
        tolerance=spec.tolerance,
        allow_exact_matches=True,
    )
    return joined.drop(columns=[spec.event_time])


def assert_no_future_rows(
    frame: pd.DataFrame, anchor_col: str, event_time_cols: list[str]
) -> None:
    """Defensive guard used in tests: no attached feature event may post-date the anchor."""

    for col in event_time_cols:
        if col not in frame.columns:
            continue
        future = frame[col] > frame[anchor_col]
        if bool(future.any()):
            raise AssertionError(
                f"{int(future.sum())} rows have {col} after {anchor_col}"
            )
