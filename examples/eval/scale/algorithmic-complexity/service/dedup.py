from __future__ import annotations

import pandas as pd


def drop_duplicate_sessions(sessions: pd.DataFrame) -> pd.DataFrame:
    ordered = sessions.sort_values(["session_id", "ended_at"])
    return ordered.drop_duplicates(subset=["session_id"], keep="last")


def filter_known_users(events: pd.DataFrame, active_user_ids: set[str]) -> pd.DataFrame:
    mask = events["user_id"].isin(active_user_ids)
    return events.loc[mask].reset_index(drop=True)


def collapse_repeat_events(events: pd.DataFrame) -> pd.DataFrame:
    seen_keys: set[tuple[str, str]] = set()
    keep_positions = []
    for row in events.itertuples(index=True):
        key = (row.session_id, row.kind)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        keep_positions.append(row.Index)
    return events.loc[keep_positions].reset_index(drop=True)
