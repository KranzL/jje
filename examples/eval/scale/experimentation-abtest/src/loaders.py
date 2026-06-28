from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExperimentFrame:
    exposures: pd.DataFrame
    sessions: pd.DataFrame
    users: pd.DataFrame


def _stable_bucket(unit_value: str, salt: str, buckets: int = 10000) -> int:
    digest = hashlib.sha256(f"{salt}:{unit_value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % buckets


def assign_variant(user_ids: pd.Series, salt: str) -> pd.Series:
    buckets = user_ids.astype(str).map(lambda u: _stable_bucket(u, salt))
    return np.where(buckets < 5000, "control", "treatment")


def load_exposures(path: str, salt: str) -> pd.DataFrame:
    exposures = pd.read_parquet(path)
    exposures = exposures.drop_duplicates(subset=["user_id"], keep="first")
    exposures["variant"] = assign_variant(exposures["user_id"], salt)
    return exposures.reset_index(drop=True)


def load_sessions(path: str) -> pd.DataFrame:
    sessions = pd.read_parquet(path)
    expected = {"user_id", "session_id", "checkout_starts", "revenue", "page_load_ms"}
    missing = expected - set(sessions.columns)
    if missing:
        raise ValueError(f"sessions missing columns: {sorted(missing)}")
    return sessions


def build_frame(exposures_path: str, sessions_path: str, salt: str) -> ExperimentFrame:
    exposures = load_exposures(exposures_path, salt)
    sessions = load_sessions(sessions_path)
    sessions = sessions.merge(
        exposures[["user_id", "variant", "exposure_ts"]],
        on="user_id",
        how="inner",
    )
    sessions = sessions[sessions["session_start_ts"] >= sessions["exposure_ts"]]

    users = (
        sessions.groupby(["user_id", "variant"], as_index=False)
        .agg(
            checkout_starts=("checkout_starts", "sum"),
            sessions=("session_id", "nunique"),
            revenue=("revenue", "sum"),
        )
    )
    return ExperimentFrame(exposures=exposures, sessions=sessions, users=users)
