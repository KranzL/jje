from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .aggregator import (
    annotate_anomalies,
    merge_engagement,
    pivot_kind_counts,
    session_event_counts,
    weighted_engagement,
)
from .dedup import (
    collapse_repeat_events,
    drop_duplicate_sessions,
    filter_known_users,
)


@dataclass(frozen=True)
class ScoringConfig:
    burst_threshold: int = 50
    decay_half_life_days: float = 7.0
    min_events: int = 1


def _recency_decay(sessions: pd.DataFrame, half_life_days: float, now: pd.Timestamp) -> pd.Series:
    age_days = (now - sessions["ended_at"]).dt.total_seconds() / 86400.0
    return 0.5 ** (age_days / half_life_days)


def build_session_scores(
    sessions: pd.DataFrame,
    events: pd.DataFrame,
    config: ScoringConfig,
    now: pd.Timestamp,
) -> pd.DataFrame:
    sessions = drop_duplicate_sessions(sessions)

    active_user_ids = set(sessions["user_id"].unique())
    events = filter_known_users(events, active_user_ids)
    events = collapse_repeat_events(events)

    annotated = annotate_anomalies(events, config.burst_threshold)
    clean_events = annotated.loc[~annotated["is_burst"]].reset_index(drop=True)

    counts = session_event_counts(clean_events)
    wide = pivot_kind_counts(counts)
    engagement = weighted_engagement(wide)

    scored = merge_engagement(sessions, engagement)
    scored["engagement"] = scored["engagement"].fillna(0.0)

    decay = _recency_decay(scored, config.decay_half_life_days, now)
    scored["score"] = scored["engagement"] * decay.values

    eligible = scored["events"] >= config.min_events
    return scored.loc[eligible].sort_values("score", ascending=False).reset_index(drop=True)


def top_sessions(scored: pd.DataFrame, k: int) -> pd.DataFrame:
    return scored.head(k)
