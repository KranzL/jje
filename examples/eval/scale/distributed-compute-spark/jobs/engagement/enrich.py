"""Daily engagement enrichment job entry point.

Reads one partition of raw clickstream events and joins them against the
reference dimensions to produce ``fct_engagement_enriched``. Join strategies are
chosen explicitly here rather than relying solely on AQE so the physical plan is
predictable across runs and cluster sizes.
"""

from __future__ import annotations

import argparse

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast

from . import reference, transforms
from .config import JobConfig, load_config


def _read_events(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    return (
        spark.table(cfg.sources.events)
        .where(cfg.event_partition_filter)
    )


def _assert_single_partition(events: DataFrame, cfg: JobConfig) -> None:
    distinct_dates = (
        events.select("event_date")
        .distinct()
        .limit(10)
        .collect()
    )
    found = {row["event_date"] for row in distinct_dates}
    if found and found != {cfg.run_date}:
        raise ValueError(
            f"events partition filter leaked dates {sorted(found)} "
            f"for run_date={cfg.run_date}"
        )


def build_enriched(spark: SparkSession, cfg: JobConfig) -> DataFrame:
    events = transforms.normalize_events(_read_events(spark, cfg))
    _assert_single_partition(events, cfg)

    country = reference.load_country_lookup(spark, cfg)
    rates = reference.load_currency_rates(spark, cfg)
    devices = reference.load_device_dim(spark, cfg)
    campaigns = reference.load_campaign_dim(spark, cfg)

    enriched = (
        events
        .join(broadcast(country), on="country_code", how="left")
        .join(
            broadcast(rates),
            on="currency_code",
            how="left",
        )
        .join(devices, on="device_id", how="left")
        .join(broadcast(campaigns), on="campaign_id", how="left")
    )

    enriched = transforms.add_revenue_usd(enriched)
    enriched = transforms.add_engagement_score(enriched)
    return transforms.select_output_columns(enriched)


def write_output(df: DataFrame, cfg: JobConfig) -> None:
    (
        df.repartition(cfg.output_partitions, "event_date")
        .write.mode("overwrite")
        .format("parquet")
        .partitionBy("event_date")
        .saveAsTable(cfg.output_table)
    )


def run(config_path: str, run_date: str) -> None:
    cfg = load_config(config_path, run_date)
    spark = (
        SparkSession.builder
        .appName(f"engagement-enrich-{run_date}")
        .config("spark.sql.shuffle.partitions", cfg.shuffle_partitions)
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    try:
        result = build_enriched(spark, cfg)
        write_output(result, cfg)
    finally:
        spark.stop()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Engagement enrichment job")
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-date", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run(args.config, args.run_date)
