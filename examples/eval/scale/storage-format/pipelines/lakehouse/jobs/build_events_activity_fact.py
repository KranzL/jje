from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from pipelines.lakehouse.writers.parquet_writer import TableWriteConfig, write_table

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "table_configs"


def load_config(name: str) -> TableWriteConfig:
    with open(_CONFIG_DIR / f"{name}.yaml") as handle:
        return TableWriteConfig.from_dict(yaml.safe_load(handle))


def build_fact(spark: SparkSession, run_date: str):
    raw = (
        spark.read.format("parquet")
        .load("s3://acme-lake/raw/app_events")
        .where(F.col("ingest_date") == F.lit(run_date))
    )

    return (
        raw.select(
            F.col("raw_event_id").alias("event_id"),
            F.col("raw_account_id").cast("bigint").alias("account_id"),
            F.get_json_object("raw_attributes_json", "$.device_id").cast("bigint").alias("device_id"),
            F.get_json_object("raw_attributes_json", "$.session_id").alias("session_id"),
            F.col("raw_event_type").alias("event_type"),
            F.col("raw_event_time").alias("event_time"),
            F.get_json_object("raw_attributes_json", "$.surface").alias("surface"),
            F.get_json_object("raw_attributes_json", "$.country_code").alias("country_code"),
            F.get_json_object("raw_attributes_json", "$.app_version").alias("app_version"),
            F.get_json_object("raw_attributes_json", "$.duration_ms").cast("bigint").alias("duration_ms"),
            F.length("raw_attributes_json").cast("bigint").alias("payload_bytes"),
            F.get_json_object("raw_attributes_json", "$.is_authenticated").cast("boolean").alias("is_authenticated"),
            F.col("ingest_date"),
        )
        .where(F.col("event_id").isNotNull())
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder.appName("build_events_activity_fact").getOrCreate()
    spark.conf.set("spark.sql.parquet.filterPushdown", "true")
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    config = load_config("events_activity_fact")
    fact = build_fact(spark, args.run_date)
    write_table(spark, fact, config)


if __name__ == "__main__":
    main()
