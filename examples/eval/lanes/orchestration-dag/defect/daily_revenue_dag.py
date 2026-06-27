from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}

with DAG(
    dag_id="daily_revenue",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=True,
    max_active_runs=1,
    default_args=default_args,
    tags=["revenue", "finance"],
    on_failure_callback=lambda context: None,
) as dag:
    run_date = datetime.now().strftime("%Y-%m-%d")

    load_partition = PostgresOperator(
        task_id="load_revenue_partition",
        postgres_conn_id="warehouse",
        pool="warehouse_pool",
        sql=f"""
            DELETE FROM analytics.daily_revenue
            WHERE revenue_date = '{run_date}';

            INSERT INTO analytics.daily_revenue (revenue_date, gross_revenue)
            SELECT order_date, SUM(amount)
            FROM raw.orders
            WHERE order_date = '{run_date}'
            GROUP BY order_date;
        """,
    )
