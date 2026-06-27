from pyspark.sql import SparkSession
from pyspark.sql import functions as F

OUTPUT_PATH = "s3://analytics-prod/marts/customer_orders"


def build_session():
    return (
        SparkSession.builder.appName("export_customer_orders")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def load_orders(spark):
    orders = spark.read.parquet("s3://lake-prod/orders")
    customers = spark.read.parquet("s3://lake-prod/customers")

    enriched = (
        orders.join(customers, on="customer_id", how="inner")
        .withColumn("order_date", F.to_date("order_ts"))
        .withColumn("net_amount", F.col("gross_amount") - F.col("discount_amount"))
        .withColumn("net_amount", F.coalesce(F.col("net_amount"), F.lit(0.0)))
        .select(
            "order_id",
            "customer_id",
            "customer_segment",
            "order_date",
            "net_amount",
        )
    )
    return enriched


def main():
    spark = build_session()
    enriched = load_orders(spark)

    (
        enriched.write.mode("overwrite")
        .partitionBy("order_date")
        .parquet(OUTPUT_PATH)
    )

    print(f"wrote customer orders to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
