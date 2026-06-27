from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, sum as _sum
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType

spark = SparkSession.builder.appName("revenue_window").getOrCreate()

schema = (
    StructType()
    .add("order_id", StringType())
    .add("merchant_id", StringType())
    .add("amount", DoubleType())
    .add("event_time", TimestampType())
)

raw = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "orders")
    .load()
)

orders = raw.select(
    from_json(col("value").cast("string"), schema).alias("o")
).select("o.*")

revenue = (
    orders.withWatermark("event_time", "30 minutes")
    .groupBy(
        col("merchant_id"),
        window(col("event_time"), "1 hour"),
    )
    .agg(_sum("amount").alias("revenue"))
)

query = (
    revenue.writeStream.format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("topic", "merchant_hourly_revenue")
    .option("checkpointLocation", "/chk/revenue_window")
    .outputMode("update")
    .start()
)

query.awaitTermination()
