from __future__ import annotations

from typing import Any

import pendulum
from airflow import DAG
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.operators.python import PythonOperator

from marketing import config
from marketing.callbacks import notify_failure, notify_sla_miss
from marketing.include import partitions

SQL_DIR = "include/sql"


def _channel_list() -> str:
    return ", ".join(f"'{c}'" for c in config.TOUCHPOINT_SOURCES)


def export_attribution_snapshot(**context: Any) -> None:
    partition_date = pendulum.now("UTC").to_date_string()
    key = partitions.s3_partition_path(config.CONVERSIONS_PREFIX, partition_date)

    hook = SnowflakeHook(snowflake_conn_id=config.WAREHOUSE_CONN_ID)
    rows = hook.get_pandas_df(
        f"""
        SELECT conversion_id, user_id, channel, campaign_id,
               touch_position, path_length, linear_credit_cents
        FROM {config.MART_SCHEMA}.fct_attribution_paths
        WHERE conversion_date = '{context['ds']}'
        """
    )

    s3 = S3Hook(aws_conn_id=config.S3_CONN_ID)
    s3.load_string(
        string_data=rows.to_csv(index=False),
        key=f"{key}snapshot.csv",
        bucket_name=config.SOURCE_BUCKET,
        replace=True,
    )


def assert_freshness(**context: Any) -> None:
    hook = SnowflakeHook(snowflake_conn_id=config.WAREHOUSE_CONN_ID)
    max_ts = hook.get_first(
        f"""
        SELECT MAX(occurred_at)
        FROM {config.STAGING_SCHEMA}.stg_touchpoints
        WHERE event_date = '{context['ds']}'
        """
    )[0]
    if max_ts is None:
        raise ValueError(f"no touchpoints staged for {context['ds']}")

    age_minutes = (pendulum.now("UTC") - pendulum.instance(max_ts)).in_minutes()
    if age_minutes > config.ATTRIBUTION_LOOKBACK_DAYS * 24 * 60:
        raise ValueError(f"stale touchpoints for {context['ds']}: {age_minutes}m old")


def record_run_audit(**context: Any) -> None:
    meta = partitions.run_metadata(context)
    hook = SnowflakeHook(snowflake_conn_id=config.WAREHOUSE_CONN_ID)
    hook.run(
        f"""
        INSERT INTO {config.MART_SCHEMA}.attribution_run_audit
            (dag_id, run_id, logical_date, ingested_at)
        VALUES (%(dag_id)s, %(run_id)s, %(logical_date)s, %(ingested_at)s)
        """,
        parameters=meta,
    )


with DAG(
    dag_id=config.DAG_ID,
    schedule=config.SCHEDULE,
    start_date=config.START_DATE,
    catchup=True,
    max_active_runs=1,
    default_args=config.DEFAULT_ARGS,
    sla_miss_callback=notify_sla_miss,
    on_failure_callback=notify_failure,
    template_searchpath=["/opt/airflow/dags/marketing"],
    tags=["marketing", "attribution", "daily"],
) as dag:

    wait_for_touchpoints = S3KeySensor(
        task_id="wait_for_touchpoints",
        bucket_name=config.SOURCE_BUCKET,
        bucket_key=f"{config.TOUCHPOINTS_PREFIX}/dt={{{{ ds }}}}/_SUCCESS",
        aws_conn_id=config.S3_CONN_ID,
        poke_interval=300,
        timeout=60 * 60,
        mode="reschedule",
    )

    stage_touchpoints = SnowflakeOperator(
        task_id="stage_touchpoints",
        snowflake_conn_id=config.WAREHOUSE_CONN_ID,
        sql=f"{SQL_DIR}/stage_touchpoints.sql",
        params={
            "staging_schema": config.STAGING_SCHEMA,
            "channel_list": _channel_list(),
        },
    )

    check_freshness = PythonOperator(
        task_id="check_freshness",
        python_callable=assert_freshness,
    )

    build_paths = SnowflakeOperator(
        task_id="build_attribution_paths",
        snowflake_conn_id=config.WAREHOUSE_CONN_ID,
        sql=f"{SQL_DIR}/build_attribution_paths.sql",
        params={
            "staging_schema": config.STAGING_SCHEMA,
            "mart_schema": config.MART_SCHEMA,
            "lookback_days": config.ATTRIBUTION_LOOKBACK_DAYS,
        },
    )

    export_snapshot = PythonOperator(
        task_id="export_attribution_snapshot",
        python_callable=export_attribution_snapshot,
    )

    audit = PythonOperator(
        task_id="record_run_audit",
        python_callable=record_run_audit,
        trigger_rule="all_done",
    )

    wait_for_touchpoints >> stage_touchpoints >> check_freshness >> build_paths
    build_paths >> export_snapshot >> audit
