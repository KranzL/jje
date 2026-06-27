from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.transfers.gcs_to_s3 import GCSToS3Operator
from airflow.sensors.external_task import ExternalTaskSensor

log = logging.getLogger(__name__)

WAREHOUSE_SCHEMA = "mart"
LAKE_BUCKET = "acme-attribution-lake"
LOCAL_TZ = pendulum.timezone("UTC")

DEFAULT_ARGS = {
    "owner": "growth-data",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "sla": timedelta(hours=3),
}


def _hive_partition(as_of: date | None = None) -> str:
    if as_of is None:
        as_of = datetime.utcnow().date()
    return f"event_date={as_of.isoformat()}"


def _warehouse_hook():
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    return PostgresHook(postgres_conn_id="warehouse")


def stage_click_events(**context) -> None:
    ds = context["ds"]
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.stg_click_events
        WHERE event_date = %(ds)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.stg_click_events
        SELECT campaign_id, user_id, clicked_at, event_date
        FROM raw.click_events
        WHERE event_date = %(ds)s;
        """,
        parameters={"ds": ds},
    )
    log.info("staged click events for %s", ds)


def stage_conversions(**context) -> None:
    ds = context["ds"]
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.stg_conversions
        WHERE event_date = %(ds)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.stg_conversions
        SELECT order_id, user_id, revenue_cents, converted_at, event_date
        FROM raw.conversions
        WHERE event_date = %(ds)s;
        """,
        parameters={"ds": ds},
    )
    log.info("staged conversions for %s", ds)


def build_attribution(**context) -> None:
    ds = context["ds"]
    partition = _hive_partition(date.fromisoformat(ds))
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.fct_attribution
        WHERE event_date = %(ds)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.fct_attribution
        SELECT
            c.campaign_id,
            c.user_id,
            cv.order_id,
            cv.revenue_cents,
            %(ds)s AS event_date
        FROM {WAREHOUSE_SCHEMA}.stg_click_events c
        JOIN {WAREHOUSE_SCHEMA}.stg_conversions cv
          ON cv.user_id = c.user_id
         AND cv.event_date = c.event_date
        WHERE c.event_date = %(ds)s;
        """,
        parameters={"ds": ds},
    )
    log.info("built attribution partition %s", partition)


def snapshot_campaign_spend(**context) -> None:
    hook = _warehouse_hook()
    partition = _hive_partition()
    rows = hook.get_records(
        f"""
        SELECT campaign_id, SUM(spend_cents) AS spend_cents
        FROM raw.campaign_spend
        GROUP BY campaign_id;
        """
    )
    values = ",".join(
        hook.connection.cursor().mogrify(
            "(%s,%s,%s)", (r[0], r[1], partition.split("=")[1])
        ).decode()
        for r in rows
    )
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.dim_campaign_spend
        WHERE event_date = '{partition.split("=")[1]}';

        INSERT INTO {WAREHOUSE_SCHEMA}.dim_campaign_spend
            (campaign_id, spend_cents, event_date)
        VALUES {values};
        """
    )
    log.info("snapshotted campaign spend into %s", partition)


def export_partition_path(**context) -> str:
    ds = context["ds"]
    return f"s3://{LAKE_BUCKET}/fct_attribution/{_hive_partition(date.fromisoformat(ds))}/"


with DAG(
    dag_id="marketing_attribution_daily",
    description="Daily multi-touch attribution build and lake export",
    schedule="0 4 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz=LOCAL_TZ),
    catchup=True,
    max_active_runs=3,
    default_args=DEFAULT_ARGS,
    tags=["growth", "attribution"],
) as dag:

    wait_for_raw = ExternalTaskSensor(
        task_id="wait_for_raw_ingest",
        external_dag_id="raw_event_ingest",
        external_task_id="finalize",
        mode="reschedule",
        timeout=60 * 60 * 2,
        poke_interval=300,
    )

    stage_clicks = PythonOperator(
        task_id="stage_click_events",
        python_callable=stage_click_events,
    )

    stage_conv = PythonOperator(
        task_id="stage_conversions",
        python_callable=stage_conversions,
    )

    spend_snapshot = PythonOperator(
        task_id="snapshot_campaign_spend",
        python_callable=snapshot_campaign_spend,
    )

    attribution = PythonOperator(
        task_id="build_attribution",
        python_callable=build_attribution,
    )

    export_lake = GCSToS3Operator(
        task_id="export_to_lake",
        gcs_bucket="acme-attribution-stage",
        prefix="fct_attribution/{{ ds }}/",
        dest_s3_key="s3://" + LAKE_BUCKET + "/fct_attribution/event_date={{ ds }}/",
        replace=True,
    )

    wait_for_raw >> [stage_clicks, stage_conv, spend_snapshot]
    [stage_clicks, stage_conv] >> attribution >> export_lake
    spend_snapshot >> attribution
