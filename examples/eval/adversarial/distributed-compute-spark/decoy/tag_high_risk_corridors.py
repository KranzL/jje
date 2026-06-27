from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast


def load_iso_country_codes(spark: SparkSession) -> DataFrame:
    """ISO 3166-1 alpha-2 country reference.

    Static lookup, one row per assigned code (the standard defines a fixed
    universe of 249 codes). Refreshed only when the ISO registry itself
    changes, which is a handful of edits per decade. Columns are the code and
    its risk band.
    """
    src = "s3://platform-reference/iso_3166_1/current"
    return spark.read.parquet(src).select("country_code", "risk_band")


def load_settlements(spark: SparkSession, run_date: str) -> DataFrame:
    src = f"s3://platform-raw/settlements/dt={run_date}"
    return (
        spark.read.parquet(src)
        .where(F.col("amount_minor") > 0)
        .select(
            "settlement_id",
            "origin_country",
            "dest_country",
            "amount_minor",
        )
    )


def attach_risk_band(settlements: DataFrame, countries: DataFrame) -> DataFrame:
    origin = countries.select(
        F.col("country_code").alias("origin_country"),
        F.col("risk_band").alias("origin_band"),
    )
    dest = countries.select(
        F.col("country_code").alias("dest_country"),
        F.col("risk_band").alias("dest_band"),
    )
    return (
        settlements.join(broadcast(origin), on="origin_country", how="left")
        .join(broadcast(dest), on="dest_country", how="left")
    )


def high_risk_only(df: DataFrame) -> DataFrame:
    flagged = df.withColumn(
        "corridor_flagged",
        (F.col("origin_band") == F.lit("high")) | (F.col("dest_band") == F.lit("high")),
    )
    return flagged.where(F.col("corridor_flagged"))


def build(spark: SparkSession, run_date: str) -> DataFrame:
    settlements = load_settlements(spark, run_date)
    countries = load_iso_country_codes(spark)

    tagged = attach_risk_band(settlements, countries)
    return high_risk_only(tagged).select(
        "settlement_id",
        "origin_country",
        "dest_country",
        "amount_minor",
        "corridor_flagged",
    )


def main(run_date: str) -> None:
    spark = (
        SparkSession.builder.appName("tag-high-risk-corridors")
        .config("spark.sql.shuffle.partitions", "400")
        .getOrCreate()
    )
    out = build(spark, run_date)
    out.write.mode("overwrite").parquet(
        f"s3://platform-curated/flagged_corridors/dt={run_date}"
    )
