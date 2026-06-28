from __future__ import annotations

from typing import Any

import pendulum


def logical_date_str(context: dict[str, Any]) -> str:
    return context["ds"]


def logical_date_nodash(context: dict[str, Any]) -> str:
    return context["ds_nodash"]


def lookback_window(context: dict[str, Any], days: int) -> tuple[str, str]:
    end = pendulum.parse(context["ds"])
    start = end.subtract(days=days - 1)
    return start.to_date_string(), end.to_date_string()


def s3_partition_path(prefix: str, partition_date: str) -> str:
    return f"{prefix}/dt={partition_date}/"


def run_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "dag_id": context["dag"].dag_id,
        "run_id": context["run_id"],
        "logical_date": context["ds"],
        "ingested_at": pendulum.now("UTC").to_iso8601_string(),
    }
