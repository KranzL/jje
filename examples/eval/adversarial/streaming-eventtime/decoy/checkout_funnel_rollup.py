from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
)

spark = (
    SparkSession.builder.appName("checkout_funnel_rollup")
    .config("spark.sql.shuffle.partitions", "64")
    .getOrCreate()
)

event_schema = StructType([
    StructField("session_id", StringType()),
    StructField("account_id", StringType()),
    StructField("step", StringType()),
    StructField("cart_value_cents", LongType()),
    StructField("occurred_at", StringType()),
])

source = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:9092,broker-2:9092")
    .option("subscribe", "checkout-events")
    .option("startingOffsets", "latest")
    .load()
)

decoded = (
    source.select(
        F.col("timestamp").alias("broker_ts"),
        F.from_json(F.col("value").cast("string"), event_schema).alias("body"),
    )
    .select("broker_ts", "body.*")
    .withColumn("ts", F.to_timestamp("occurred_at"))
    .withColumn("ingested_at", F.current_timestamp())
    .where(F.col("session_id").isNotNull() & F.col("ts").isNotNull())
)

funnel = (
    decoded.withWatermark("ts", "30 minutes")
    .groupBy(
        F.window("ts", "10 minutes"),
        F.col("step"),
    )
    .agg(
        F.approx_count_distinct("session_id").alias("sessions"),
        F.sum("cart_value_cents").alias("cart_value_cents"),
        F.max("broker_ts").alias("last_broker_ts"),
        F.max("ingested_at").alias("last_ingested_at"),
    )
    .select(
        F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"),
        "step",
        "sessions",
        "cart_value_cents",
        "last_broker_ts",
        "last_ingested_at",
    )
)

query = (
    funnel.writeStream.outputMode("append")
    .format("delta")
    .option("checkpointLocation", "s3://funnel/_checkpoints/step_rollup")
    .trigger(processingTime="2 minutes")
    .toTable("mart.checkout_funnel_10m")
)

query.awaitTermination()
