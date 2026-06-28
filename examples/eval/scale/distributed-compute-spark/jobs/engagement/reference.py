"""Loaders for the small reference dimensions used during enrichment.

Each loader returns a DataFrame already projected down to the columns the join
needs, so the planner sees the narrowest possible scan. Broadcast decisions are
made by the caller in :mod:`jobs.engagement.enrich`, not here, so that the join
strategy stays visible at the call site.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .config import JobConfig


def load_country_lookup(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    """ISO country reference. Static seed table, ~250 rows, edited by hand."""
    return (
        spark.table(cfg.sources.country_lookup)
        .select(
            F.col("country_code"),
            F.col("region"),
            F.col("is_gdpr_region"),
        )
    )


def load_currency_rates(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    """Daily FX snapshot. One row per currency for the run date (~160 rows)."""
    return (
        spark.table(cfg.sources.currency_rates)
        .where(F.col("rate_date") == F.lit(cfg.run_date))
        .select(
            F.col("currency_code"),
            F.col("usd_rate"),
        )
    )


def load_device_dim(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    """Device dimension keyed by device_id.

    Large and high cardinality (hundreds of millions of devices); always joined
    with the default strategy and never collected or broadcast.
    """
    return (
        spark.table(cfg.sources.device_dim)
        .select(
            F.col("device_id"),
            F.col("device_class"),
            F.col("os_family"),
        )
    )


def load_campaign_dim(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    """Campaign dimension keyed by campaign_id.

    Append-only marketing dimension: every campaign ever launched is retained
    for attribution history. Returns the full table projected to the attributes
    enrichment needs.
    """
    return (
        spark.table(cfg.sources.campaign_dim)
        .select(
            F.col("campaign_id"),
            F.col("campaign_name"),
            F.col("channel"),
            F.col("acquisition_cost_currency"),
        )
    )
