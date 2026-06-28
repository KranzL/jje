from __future__ import annotations

import pandas as pd


WEIGHTED_KINDS = {
    "purchase": 5.0,
    "add_to_cart": 2.0,
    "view": 0.5,
    "search": 0.25,
}


def session_event_counts(events: pd.DataFrame) -> pd.DataFrame:
    counts = (
        events.groupby(["session_id", "kind"])
        .size()
        .rename("n")
        .reset_index()
    )
    return counts


def pivot_kind_counts(counts: pd.DataFrame) -> pd.DataFrame:
    wide = counts.pivot_table(
        index="session_id",
        columns="kind",
        values="n",
        fill_value=0,
        aggfunc="sum",
    )
    return wide.reset_index()


def weighted_engagement(wide: pd.DataFrame) -> pd.DataFrame:
    out = wide[["session_id"]].copy()
    score = pd.Series(0.0, index=wide.index)
    for kind, weight in WEIGHTED_KINDS.items():
        if kind in wide.columns:
            score = score + wide[kind] * weight
    out["engagement"] = score.values
    return out


def find_anomalous_sessions(events: pd.DataFrame, burst_threshold: int) -> pd.DataFrame:
    per_session = events.groupby("session_id").size().rename("n").reset_index()
    return per_session.loc[per_session["n"] >= burst_threshold]


def annotate_anomalies(events: pd.DataFrame, burst_threshold: int) -> pd.DataFrame:
    anomalies = find_anomalous_sessions(events, burst_threshold)
    flagged_sessions = anomalies["session_id"].tolist()

    annotated = events.copy()
    is_burst = []
    for row in annotated.itertuples(index=False):
        if row.session_id in flagged_sessions:
            is_burst.append(True)
        else:
            is_burst.append(False)
    annotated["is_burst"] = is_burst
    return annotated


def merge_engagement(sessions: pd.DataFrame, engagement: pd.DataFrame) -> pd.DataFrame:
    return sessions.merge(engagement, on="session_id", how="left")
