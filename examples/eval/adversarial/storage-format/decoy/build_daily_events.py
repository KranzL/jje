from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def _normalize_merchant(df):
    return df.withColumn(
        "merchant_name",
        F.trim(F.upper(F.col("merchant_name"))),
    )


def build_daily_events(spark, src, dst):
    events = spark.read.parquet(src)
    events = _normalize_merchant(events)

    events = (
        events
        .withColumn("event_ts", F.to_timestamp(F.col("event_ts")))
        .withColumn("dt", F.date_format(F.col("event_ts"), "yyyy-MM-dd"))
        .withColumn("net_amount", F.col("gross_amount") - F.col("fee_amount"))
        .withColumn("hour_of_day", F.hour(F.col("event_ts")))
    )

    cleaned = (
        events
        .where(F.col("net_amount") >= 0)
        .dropDuplicates(["event_id"])
    )

    (
        cleaned
        .repartitionByRange(64, "event_ts")
        .sortWithinPartitions("event_ts")
        .write
        .mode("overwrite")
        .option("compression", "zstd")
        .partitionBy("dt")
        .parquet(dst)
    )


if __name__ == "__main__":
    spark = SparkSession.builder.appName("daily_events").getOrCreate()
    build_daily_events(
        spark,
        "s3://lake/raw/events/",
        "s3://lake/curated/daily_events/",
    )
