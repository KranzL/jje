from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


SESSION_COLUMNS = [
    "session_id",
    "user_id",
    "started_at",
    "ended_at",
    "platform",
    "events",
]

EVENT_COLUMNS = [
    "event_id",
    "session_id",
    "user_id",
    "kind",
    "ts",
    "value",
]


@dataclass(frozen=True)
class LoadSpec:
    root: Path
    partitions: tuple[str, ...]

    def session_paths(self) -> list[Path]:
        return [self.root / p / "sessions.parquet" for p in self.partitions]

    def event_paths(self) -> list[Path]:
        return [self.root / p / "events.parquet" for p in self.partitions]


def _read_many(paths: Iterable[Path], columns: list[str]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if not path.exists():
            continue
        frame = pd.read_parquet(path, columns=columns)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def load_sessions(spec: LoadSpec) -> pd.DataFrame:
    sessions = _read_many(spec.session_paths(), SESSION_COLUMNS)
    sessions["started_at"] = pd.to_datetime(sessions["started_at"], utc=True)
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"], utc=True)
    return sessions


def load_events(spec: LoadSpec) -> pd.DataFrame:
    events = _read_many(spec.event_paths(), EVENT_COLUMNS)
    events["ts"] = pd.to_datetime(events["ts"], utc=True)
    return events
