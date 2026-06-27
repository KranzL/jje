from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast


def load_partner_registry(spark: SparkSession, run_date: str) -> DataFrame:
    """Partner registry snapshot for the given processing date.

    Sourced from the onboarding service export. The pilot cohort that seeded
    this table was a few hundred partners; the export now lands one row per
    active partner-region pair and continues to accumulate as new markets are
    switched on each quarter. Region split is roughly uniform.
    """
    src = f"s3://platform-curated/partner_registry/dt={run_date}"
    return (
        spark.read.parquet(src)
        .where(F.col("status") == "active")
        .select(
            "partner_id",
            "region_code",
            "settlement_tier",
            "display_name",
        )
    )


def load_transactions(spark: SparkSession, run_date: str) -> DataFrame:
    src = f"s3://platform-raw/transactions/dt={run_date}"
    return (
        spark.read.parquet(src)
        .where(F.col("amount_minor") > 0)
        .select(
            "txn_id",
            "partner_id",
            "region_code",
            "amount_minor",
            "currency",
            "captured_at",
        )
    )


def load_fx_rates(spark: SparkSession, run_date: str) -> DataFrame:
    src = f"s3://platform-curated/fx_rates/dt={run_date}"
    return spark.read.parquet(src).select("currency", "rate_to_usd")


def attach_settlement_attributes(txns: DataFrame, registry: DataFrame) -> DataFrame:
    keyed = registry.withColumnRenamed("display_name", "partner_name")
    return txns.join(
        broadcast(keyed),
        on=["partner_id", "region_code"],
        how="left",
    )


def attach_usd_amount(txns: DataFrame, fx: DataFrame) -> DataFrame:
    rates = fx.hint("broadcast")
    joined = txns.join(rates, on="currency", how="left")
    return joined.withColumn(
        "amount_usd",
        F.col("amount_minor") / F.lit(100.0) * F.coalesce(F.col("rate_to_usd"), F.lit(1.0)),
    )


def build(spark: SparkSession, run_date: str) -> DataFrame:
    txns = load_transactions(spark, run_date)
    registry = load_partner_registry(spark, run_date)
    fx = load_fx_rates(spark, run_date)

    enriched = attach_settlement_attributes(txns, registry)
    enriched = attach_usd_amount(enriched, fx)

    return enriched.select(
        "txn_id",
        "partner_id",
        "partner_name",
        "region_code",
        "settlement_tier",
        "amount_usd",
        "captured_at",
    )


def main(run_date: str) -> None:
    spark = (
        SparkSession.builder.appName("enrich-transactions")
        .config("spark.sql.shuffle.partitions", "400")
        .getOrCreate()
    )
    out = build(spark, run_date)
    (
        out.write.mode("overwrite")
        .partitionBy("region_code")
        .parquet(f"s3://platform-curated/transactions_enriched/dt={run_date}")
    )
