from __future__ import annotations

import pandas as pd

from service.aggregator import (
    annotate_anomalies,
    pivot_kind_counts,
    session_event_counts,
    weighted_engagement,
)
from service.dedup import collapse_repeat_events, filter_known_users
from service.scoring import ScoringConfig, build_session_scores, top_sessions


def _events():
    return pd.DataFrame(
        {
            "event_id": [f"e{i}" for i in range(6)],
            "session_id": ["s1", "s1", "s1", "s2", "s2", "s3"],
            "user_id": ["u1", "u1", "u1", "u2", "u2", "u9"],
            "kind": ["view", "view", "purchase", "view", "add_to_cart", "search"],
            "ts": pd.to_datetime(
                [
                    "2026-06-01T00:00:00Z",
                    "2026-06-01T00:01:00Z",
                    "2026-06-01T00:02:00Z",
                    "2026-06-02T00:00:00Z",
                    "2026-06-02T00:01:00Z",
                    "2026-06-03T00:00:00Z",
                ]
            ),
            "value": [1.0, 1.0, 9.0, 1.0, 3.0, 1.0],
        }
    )


def _sessions():
    return pd.DataFrame(
        {
            "session_id": ["s1", "s2"],
            "user_id": ["u1", "u2"],
            "started_at": pd.to_datetime(["2026-06-01T00:00:00Z", "2026-06-02T00:00:00Z"]),
            "ended_at": pd.to_datetime(["2026-06-01T00:03:00Z", "2026-06-02T00:02:00Z"]),
            "platform": ["ios", "web"],
            "events": [3, 2],
        }
    )


def test_filter_known_users_drops_unknown():
    events = _events()
    kept = filter_known_users(events, {"u1", "u2"})
    assert set(kept["user_id"]) == {"u1", "u2"}


def test_collapse_repeat_events_keeps_first_per_kind():
    events = _events()
    collapsed = collapse_repeat_events(events)
    s1 = collapsed.loc[collapsed["session_id"] == "s1"]
    assert sorted(s1["kind"]) == ["purchase", "view"]


def test_weighted_engagement_matches_weights():
    events = filter_known_users(_events(), {"u1", "u2"})
    wide = pivot_kind_counts(session_event_counts(events))
    eng = weighted_engagement(wide).set_index("session_id")["engagement"]
    assert eng.loc["s1"] == 0.5 * 2 + 5.0
    assert eng.loc["s2"] == 0.5 + 2.0


def test_annotate_anomalies_flags_high_volume():
    events = _events()
    annotated = annotate_anomalies(events, burst_threshold=3)
    assert annotated.loc[annotated["session_id"] == "s1", "is_burst"].all()
    assert not annotated.loc[annotated["session_id"] == "s2", "is_burst"].any()


def test_build_session_scores_orders_by_score():
    now = pd.Timestamp("2026-06-04T00:00:00Z")
    scored = build_session_scores(_sessions(), _events(), ScoringConfig(burst_threshold=100), now)
    assert list(scored["session_id"]) == ["s1", "s2"]
    assert top_sessions(scored, 1).iloc[0]["session_id"] == "s1"
