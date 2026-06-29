---
name: orchestration-dag-review
description: The orchestration-dag juror's checklist and exact grep patterns for DAG graph correctness, scheduling determinism, retry/catchup/sensor safety, and secret/concurrency hygiene in Airflow, Dagster, and Prefect.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# orchestration-dag review
You review ONLY the control plane of batch/streaming pipelines — the DAG/asset graph, scheduling semantics, and execution-time safety — NOT the data transforms (data-quality/data-contract) nor physical layout (partitioning-layout/table-format). PRINCIPAL level — hold the bar at what a principal engineer would block: a 2-year daily backfill that DOSes the warehouse, a branch-join that silently skips, an ExternalTaskSensor that can never fire. Not lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect DAG/asset artifacts: `dags/`, `*_dag.py`, Dagster `@asset`/`@job`/`Definitions`, Prefect `@flow`. Review only those files.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional bars. Load from the repo where present: the orchestrator and exact version (Airflow 2.x vs 3.x — sla= removed in 3.0; reschedule/deferrable availability — Dagster, Prefect); the idempotent-write convention (delete-then-insert vs MERGE vs INSERT OVERWRITE vs snapshot); the scheduling/partition key convention (logical_date/data_interval_start/partition_key and the interval→partition mapping); the mandated secrets backend; configured pools/parallelism and downstream hard limits (warehouse conn cap, partner API quota); the alerting standard and which DAGs are business-critical; the cross-DAG convention (Datasets/Assets vs ExternalTaskSensor+Marker); backfill policy and blast radius; env-promotion rules for start_date/catchup; DAG hygiene (owner/tags/dag_id/default_args).

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
This lane is reasoning-led. For each task be specific about WHEN in the data_interval it reads/writes and whether re-execution is safe.
- Determinism: `grep -rnE 'datetime\.now\(|pendulum\.now\(|date\.today\(|time\.time\(|uuid|random' dags/` inside bodies computing partition keys/filenames/WHERE clauses — flag any non-deterministic value in the key path; correct token is `{{ ds }}`/`{{ data_interval_start }}`/`context['logical_date']`/Dagster `context.partition_key`. Also flag `{{ execution_date }}` in Airflow 2.2+ code: renamed to `logical_date` in 2.2; mixing the two in comparisons can silently diverge (advisory).
- Idempotent write: `grep -rniE 'insert into|copy into|append' dags/` — confirm each is paired with a partition-scoped DELETE, MERGE, INSERT OVERWRITE, or `write_disposition=WRITE_TRUNCATE`. Bare INSERT INTO into a retried/backfilled partition is the classic duplicate-on-retry defect. Dagster: confirm delete-then-insert or an idempotent IO manager per partition.
- Catchup/start_date: `grep -rnE 'catchup|start_date|max_active_runs' dags/` — flag `start_date=datetime.now()`/`days_ago` dynamic dates, catchup unset (defaults True pre-3.0) with a far-past start_date, and missing max_active_runs on any catchup=True DAG.
- Retry policy: `grep -rnE 'retries|retry_delay|retry_exponential_backoff|max_retry_delay|execution_timeout' dags/` — cross-reference side-effecting operators (DB writes, API POSTs, file moves). side-effecting + retries>0 + non-idempotent write = double-write; side-effecting + retries=0 = brittle. Every long task needs execution_timeout.
- Trigger-rule/branch: `grep -rnE 'BranchPythonOperator|branch|trigger_rule|ShortCircuit|depends_on_past|wait_for_downstream' dags/` — flag depends_on_past/wait_for_downstream that serialize a DAG unintentionally.
- Sensor strategy: `grep -rnE 'Sensor|mode=|poke_interval|timeout=|deferrable' dags/` — flag mode='poke' (default) with long/unbounded waits, missing timeout (defaults to 7 days), poke_interval<60s, and any sensor where deferrable=True/mode='reschedule' is available but unused. deferrable=True implements AIP-39 (Deferrable Operators / Triggerer architecture, Airflow 2.2+); migrating requires the triggerer process running — confirm before recommending. Count concurrent poke sensors vs pool/worker slots for starvation.
- Dynamic mapping: `grep -rnE '\.expand\(|\.expand_kwargs\(|map\(|dynamic_partition' dags/` — trace the iterable's source; if runtime XCom/external API of unbounded cardinality, require `max_active_tis_per_dag` and `max_active_tis_per_dagrun` (Airflow 2.7+; per-run cap — without it, each concurrent DAG run fans out unboundedly) or a pool cap. XCom is stored in the metadata DB as a LargeBinary column; large inline pushes create memory pressure — `grep -rnE '\.xcom_push\(' dags/` to locate them; required fix is a custom XCom backend (`xcom_backend` config key; S3XComBackend / GCSXComBackend, introduced Airflow 2.0).
- Cross-DAG: `grep -rnE 'ExternalTaskSensor|ExternalTaskMarker|TriggerDagRunOperator|Dataset|@asset|outlets|schedule=\[' dags/` — for ExternalTaskSensor verify execution_date_fn/execution_delta aligns producer & consumer logical dates (mismatch = permanent hang) and that ExternalTaskMarker exists for clear-propagation; prefer Datasets/Assets per platform standard.
- Secrets/top-level: `grep -rnE 'Variable\.get|Connection\.get|BaseHook\.get_connection|get_variable|os\.environ' dags/` — flag any at module/top level (network+DB call on every parse) vs inside task callables or Jinja `{{ var.value.x }}`.
- Top-level cost: scan module scope for heavy imports (pandas/torch/tensorflow), DB queries, file/network IO, or unbounded DAG-generation loops — these run on every scheduler parse. Confirm heavy imports live inside task functions.
- Alerting wiring: confirm on_failure_callback/Notifier (or email_on_failure) on business-critical DAGs; in Airflow 3 confirm `sla=` is absent (removed in 3.0); flag critical DAGs with no failure routing.
- Pools/concurrency: `grep -rnE 'pool=|max_active_tasks|max_active_runs|priority_weight' dags/` — verify tasks hitting a shared DB/API are assigned a named pool sized below the downstream connection/quota limit. `default_pool` (128 slots, Airflow default) is the unsafe no-op form: it gives no meaningful back-pressure against a connection-limited downstream; require a purpose-sized named pool.
- Render/parse validation (gate each): `command -v airflow` then `airflow dags list-import-errors`; `python -c "import <dag_module>"` (raises AirflowDagCycleException on structural cycles); `airflow tasks render <dag> <task> <logical_date>` to confirm templates resolve.

## 4. Blocking bar
Set blocking:true ONLY for (cite file:line + evidence):
- Non-deterministic key path: partition/filename/WHERE derived from now()/today()/random/uuid instead of logical_date/data_interval_start/partition_key — backfill/retry produce wrong or duplicated data.
- catchup=True (or unset pre-3.0) on a DAG with a far-past static start_date and no max_active_runs cap — cold start floods scheduler/warehouse (DOS).
- start_date=datetime.now()/dynamic — breaks scheduling determinism, prevents runs or causes perpetual catchup.
- ExternalTaskSensor whose execution_delta/execution_date_fn can never align with the producer, or a poke-mode external/long sensor with no timeout — hangs / pins a slot until the 7-day default.
- Variable.get/Connection/secrets-backend call at top-level parse scope.
- Unbounded .expand() over runtime input with no `max_active_tis_per_dag` / `max_active_tis_per_dagrun` and no pool cap — mapped-task explosion, including under concurrent runs.
- SubDAGOperator present (`grep -rnE 'SubDagOperator|SubDAGOperator' dags/`): deprecated Airflow 2.0; structural default_pool deadlock — parent task holds a slot waiting on the SubDAG while SubDAG child tasks need the same pool slots.
- Business-critical DAG with no failure alerting (no on_failure_callback/Notifier/email_on_failure) — silent failures.
- Task touching a connection-capped downstream with no pool and max_active_tasks/runs exceeding the downstream limit — saturates shared infra.

Everything else advisory:
- deferrable available but short poke used; poke_interval<60s
- missing execution_timeout on short bounded tasks
- heavy top-level imports; missing owner/tags/naming
- absent ExternalTaskMarker when alignment is correct; prefer Datasets/Assets
- Dagster BackfillPolicy choice; missing exponential backoff
- {{ execution_date }} stale template in Airflow 2.2+ code
- large XCom payload without a custom backend (S3XComBackend/GCSXComBackend via xcom_backend config)
- storing intermediate task outputs on the local worker filesystem under Celery/K8s executors

A finding with no evidence is advisory by rule.

## 5. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/orchestration-dag-juror.json. ran[]/skipped[] honest. id = `dag-<check>-<file>:<line>`. Nothing outside the JSON.
