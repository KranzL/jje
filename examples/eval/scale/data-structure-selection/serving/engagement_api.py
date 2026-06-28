from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from fastapi import APIRouter, Query

from .warehouse import WarehouseClient, get_client

router = APIRouter(prefix="/v1/engagement", tags=["engagement"])

DEFAULT_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 30


@dataclass(frozen=True)
class EngagementPoint:
    engagement_date: str
    session_hour: str
    unique_viewers: int
    countries_reached: int
    total_watch_hours: float
    median_session_ms: float
    p95_session_ms: float
    completion_rate: float


def _resolve_window(window_days: int) -> date:
    bounded = max(1, min(window_days, MAX_WINDOW_DAYS))
    return date.today() - timedelta(days=bounded)


def _rows_to_points(rows: Sequence[dict]) -> list[EngagementPoint]:
    return [
        EngagementPoint(
            engagement_date=str(r["engagement_date"]),
            session_hour=str(r["session_start_hour"]),
            unique_viewers=int(r["unique_viewers"]),
            countries_reached=int(r["countries_reached"]),
            total_watch_hours=float(r["total_watch_hours"]),
            median_session_ms=float(r["median_session_ms"]),
            p95_session_ms=float(r["p95_session_ms"]),
            completion_rate=float(r["completion_rate"]),
        )
        for r in rows
    ]


ENGAGEMENT_QUERY = """
    select
      creator_id,
      session_start_hour,
      engagement_date,
      unique_viewers,
      countries_reached,
      videos_watched,
      completions,
      total_watch_hours,
      median_session_ms,
      p95_session_ms,
      completion_rate,
      avg_rebuffer_ratio
    from analytics.agg_creator_engagement_hourly
    where creator_id = :creator_id
      and engagement_date >= :since
    order by session_start_hour
"""


@router.get("/creators/{creator_id}/hourly")
def get_creator_engagement(
    creator_id: str,
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=MAX_WINDOW_DAYS),
    client: WarehouseClient | None = None,
) -> list[EngagementPoint]:
    client = client or get_client()
    since = _resolve_window(window_days)
    rows = client.query(
        ENGAGEMENT_QUERY,
        params={"creator_id": creator_id, "since": since.isoformat()},
    )
    return _rows_to_points(rows)


@router.get("/creators/{creator_id}/summary")
def get_creator_summary(
    creator_id: str,
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=MAX_WINDOW_DAYS),
    client: WarehouseClient | None = None,
) -> dict:
    points = get_creator_engagement(creator_id, window_days, client)
    if not points:
        return {"creator_id": creator_id, "points": 0}

    peak = max(points, key=lambda p: p.unique_viewers)
    return {
        "creator_id": creator_id,
        "points": len(points),
        "peak_unique_viewers": peak.unique_viewers,
        "peak_hour": peak.session_hour,
        "total_watch_hours": round(sum(p.total_watch_hours for p in points), 2),
    }
