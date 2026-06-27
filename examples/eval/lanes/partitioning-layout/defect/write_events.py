from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("write_events").getOrCreate()

events = spark.read.parquet("s3://lake/raw/events/")

(
    events
    .write
    .format("parquet")
    .mode("overwrite")
    .partitionBy("user_id")
    .save("s3://lake/curated/events/")
)
