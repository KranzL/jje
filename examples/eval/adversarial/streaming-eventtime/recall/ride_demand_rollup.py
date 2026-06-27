from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
)

spark = (
    SparkSession.builder.appName("ride_demand_rollup")
    .config("spark.sql.shuffle.partitions", "64")
    .config("spark.sql.streaming.stateStore.providerClass",
            "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")
    .getOrCreate()
)

request_schema = StructType([
    StructField("ride_id", StringType()),
    StructField("rider_id", StringType()),
    StructField("zone_id", StringType()),
    StructField("fare_amount", DoubleType()),
    StructField("requested_at", StringType()),
    StructField("client_app_version", StringType()),
])

zones = spark.read.table("ref.surge_zones").select("zone_id", "city", "is_airport")

source = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:9092,broker-2:9092")
    .option("subscribe", "ride-requests")
    .option("startingOffsets", "latest")
    .option("maxOffsetsPerTrigger", 500000)
    .load()
)

decoded = (
    source.select(
        F.col("timestamp").alias("arrival_ts"),
        F.col("partition").alias("kafka_partition"),
        F.from_json(F.col("value").cast("string"), request_schema).alias("body"),
    )
    .select("arrival_ts", "kafka_partition", "body.*")
    .withColumn("requested_at", F.to_timestamp("requested_at"))
    .where(F.col("ride_id").isNotNull() & (F.col("fare_amount") >= 0))
)

enriched = (
    decoded.join(F.broadcast(zones), on="zone_id", how="left")
    .withColumn("event_ts", F.col("arrival_ts"))
)

rollup = (
    enriched.withWatermark("event_ts", "15 minutes")
    .groupBy(
        F.window("event_ts", "5 minutes", "5 minutes"),
        F.col("zone_id"),
        F.col("city"),
    )
    .agg(
        F.count("ride_id").alias("requests"),
        F.approx_count_distinct("rider_id").alias("unique_riders"),
        F.sum("fare_amount").alias("gross_fare"),
    )
    .select(
        F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"),
        "zone_id",
        "city",
        "requests",
        "unique_riders",
        "gross_fare",
    )
)

query = (
    rollup.writeStream.outputMode("append")
    .format("delta")
    .option("checkpointLocation", "s3://demand/_checkpoints/zone_rollup")
    .option("mergeSchema", "false")
    .partitionBy("city")
    .trigger(processingTime="1 minute")
    .toTable("mart.zone_demand_5m")
)

query.awaitTermination()
