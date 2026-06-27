from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

log = logging.getLogger(__name__)

WAREHOUSE_SCHEMA = "mart"
LAKE_BUCKET = "acme-inventory-lake"
LOCAL_TZ = pendulum.timezone("UTC")

DEFAULT_ARGS = {
    "owner": "supply-data",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "sla": timedelta(hours=3),
}


def _hive_partition(as_of: date) -> str:
    return f"snapshot_date={as_of.isoformat()}"


def _warehouse_hook():
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    return PostgresHook(postgres_conn_id="warehouse")


def stage_inventory_levels(**context) -> None:
    ds = context["ds"]
    loaded_at = datetime.now(tz=timezone.utc)
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.stg_inventory_levels
        WHERE snapshot_date = %(ds)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.stg_inventory_levels
            (sku, warehouse_id, on_hand, snapshot_date, loaded_at)
        SELECT sku, warehouse_id, on_hand, snapshot_date, %(loaded_at)s
        FROM raw.inventory_levels
        WHERE snapshot_date = %(ds)s;
        """,
        parameters={"ds": ds, "loaded_at": loaded_at},
    )
    log.info("staged inventory for %s (loaded_at=%s)", ds, loaded_at.isoformat())


def stage_reorder_points(**context) -> None:
    ds = context["ds"]
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.stg_reorder_points
        WHERE snapshot_date = %(ds)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.stg_reorder_points
        SELECT sku, warehouse_id, reorder_point, snapshot_date
        FROM raw.reorder_points
        WHERE snapshot_date = %(ds)s;
        """,
        parameters={"ds": ds},
    )
    log.info("staged reorder points for %s", ds)


def build_stockout_risk(**context) -> None:
    logical = context["data_interval_start"]
    as_of = logical.date()
    partition = _hive_partition(as_of)
    audit_ts = pendulum.now("UTC")
    hook = _warehouse_hook()
    hook.run(
        f"""
        DELETE FROM {WAREHOUSE_SCHEMA}.fct_stockout_risk
        WHERE snapshot_date = %(snapshot)s;

        INSERT INTO {WAREHOUSE_SCHEMA}.fct_stockout_risk
            (sku, warehouse_id, on_hand, reorder_point, at_risk, snapshot_date, computed_at)
        SELECT
            i.sku,
            i.warehouse_id,
            i.on_hand,
            r.reorder_point,
            (i.on_hand < r.reorder_point) AS at_risk,
            %(snapshot)s AS snapshot_date,
            %(computed_at)s AS computed_at
        FROM {WAREHOUSE_SCHEMA}.stg_inventory_levels i
        JOIN {WAREHOUSE_SCHEMA}.stg_reorder_points r
          ON r.sku = i.sku
         AND r.warehouse_id = i.warehouse_id
         AND r.snapshot_date = i.snapshot_date
        WHERE i.snapshot_date = %(snapshot)s;
        """,
        parameters={"snapshot": as_of.isoformat(), "computed_at": audit_ts},
    )
    log.info("built %s at %s", partition, audit_ts.isoformat())


def export_path(**context) -> str:
    as_of = context["data_interval_start"].date()
    return f"s3://{LAKE_BUCKET}/fct_stockout_risk/{_hive_partition(as_of)}/"


with DAG(
    dag_id="inventory_snapshot_daily",
    description="Daily inventory stockout-risk snapshot",
    schedule="0 5 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz=LOCAL_TZ),
    catchup=True,
    max_active_runs=3,
    default_args=DEFAULT_ARGS,
    tags=["supply", "inventory"],
) as dag:

    wait_for_raw = ExternalTaskSensor(
        task_id="wait_for_raw_ingest",
        external_dag_id="raw_inventory_ingest",
        external_task_id="finalize",
        mode="reschedule",
        timeout=60 * 60 * 2,
        poke_interval=300,
    )

    stage_levels = PythonOperator(
        task_id="stage_inventory_levels",
        python_callable=stage_inventory_levels,
    )

    stage_reorder = PythonOperator(
        task_id="stage_reorder_points",
        python_callable=stage_reorder_points,
    )

    risk = PythonOperator(
        task_id="build_stockout_risk",
        python_callable=build_stockout_risk,
    )

    wait_for_raw >> [stage_levels, stage_reorder] >> risk
