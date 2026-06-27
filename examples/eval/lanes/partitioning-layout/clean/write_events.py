from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("write_events").getOrCreate()

events = spark.read.parquet("s3://lake/raw/events/")

(
    events
    .write
    .format("parquet")
    .mode("overwrite")
    .partitionBy("event_date")
    .save("s3://lake/curated/events/")
)
