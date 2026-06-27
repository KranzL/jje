from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("fact_events_load").getOrCreate()

fact_events = spark.read.table("staging.events_enriched")

(
    fact_events.write
    .mode("overwrite")
    .partitionBy("event_date")
    .format("parquet")
    .option("compression", "snappy")
    .save("s3://datalake/warehouse/fact_events")
)
