from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("fact_events_load").getOrCreate()

fact_events = spark.read.table("staging.events_enriched")

(
    fact_events.write
    .mode("overwrite")
    .partitionBy("event_date")
    .format("csv")
    .option("header", "true")
    .save("s3://datalake/warehouse/fact_events")
)
