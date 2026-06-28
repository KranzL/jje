"""Unit tests for the pure column transforms.

These run against a local SparkSession with tiny in-memory frames; they do not
exercise the join strategies in :mod:`jobs.engagement.enrich`.
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession

from jobs.engagement import transforms


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("transform-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_normalize_events_uppercases_codes(spark):
    df = spark.createDataFrame(
        [(" us ", "usd", "2026-06-01 00:00:00", None)],
        ["country_code", "currency_code", "event_ts", "session_id"],
    )
    out = transforms.normalize_events(df).collect()[0]
    assert out["country_code"] == "US"
    assert out["currency_code"] == "USD"
    assert out["session_id"] == "unknown"


def test_revenue_usd_handles_missing_rate(spark):
    df = spark.createDataFrame(
        [(10.0, 1.1), (10.0, None)],
        ["revenue_local", "usd_rate"],
    )
    rows = transforms.add_revenue_usd(df).collect()
    assert rows[0]["revenue_usd"] == pytest.approx(11.0)
    assert rows[1]["revenue_usd"] is None


def test_engagement_score_is_capped(spark):
    df = spark.createDataFrame(
        [(500, 400.0, 9000.0)],
        ["click_count", "scroll_depth_pct", "dwell_seconds"],
    )
    out = transforms.add_engagement_score(df).collect()[0]
    assert out["engagement_score"] == 100.0
