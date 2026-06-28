"""Pure column transforms applied to the engagement event stream.

These functions take and return DataFrames and contain no actions, so they are
cheap to unit test against tiny in-memory frames.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def normalize_events(events: DataFrame) -> DataFrame:
    return (
        events
        .withColumn("country_code", F.upper(F.trim(F.col("country_code"))))
        .withColumn("currency_code", F.upper(F.trim(F.col("currency_code"))))
        .withColumn(
            "event_ts",
            F.to_timestamp(F.col("event_ts")),
        )
        .withColumn(
            "session_id",
            F.coalesce(F.col("session_id"), F.lit("unknown")),
        )
    )


def add_revenue_usd(events: DataFrame) -> DataFrame:
    return events.withColumn(
        "revenue_usd",
        F.when(
            F.col("usd_rate").isNotNull(),
            F.round(F.col("revenue_local") * F.col("usd_rate"), 4),
        ).otherwise(F.lit(None)),
    )


def add_engagement_score(events: DataFrame) -> DataFrame:
    weighted = (
        F.col("click_count") * F.lit(1.0)
        + F.col("scroll_depth_pct") * F.lit(0.25)
        + F.col("dwell_seconds") * F.lit(0.05)
    )
    return events.withColumn(
        "engagement_score",
        F.round(F.least(weighted, F.lit(100.0)), 2),
    )


def select_output_columns(events: DataFrame) -> DataFrame:
    return events.select(
        "event_id",
        "event_date",
        "event_ts",
        "user_id",
        "session_id",
        "device_id",
        "device_class",
        "os_family",
        "country_code",
        "region",
        "is_gdpr_region",
        "campaign_id",
        "campaign_name",
        "channel",
        "revenue_usd",
        "engagement_score",
    )
