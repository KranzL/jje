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
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions), treat its blocking rules as additional bars. Load from the repo where present: the orchestrator and exact version (Airflow 2.x vs 3.x — sla removed in 3.0, Deadline Alerts in 3.1; reschedule/deferrable availability — Dagster, Prefect); the idempotent-write convention (delete-then-insert vs MERGE vs INSERT OVERWRITE vs snapshot); the scheduling/partition key convention (logical_date/data_interval_start/partition_key and the interval→partition mapping); the mandated secrets backend; configured pools/parallelism and downstream hard limits (warehouse conn cap, partner API quota); the alerting standard and which DAGs are business-critical; the cross-DAG convention (Datasets/Assets vs ExternalTaskSensor+Marker); backfill policy and blast radius; env-promotion rules for start_date/catchup; DAG hygiene (owner/tags/dag_id/default_args).

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
This lane is reasoning-led. For each task be specific about WHEN in the data_interval it reads/writes and whether re-execution is safe.
- Determinism: `grep -rnE 'datetime\.now\(|pendulum\.now\(|date\.today\(|time\.time\(|uuid|random' dags/` inside bodies computing partition keys/filenames/WHERE clauses — flag any non-deterministic value in the key path; correct token is `{{ ds }}`/`{{ data_interval_start }}`/`context['logical_date']`/Dagster `context.partition_key`.
- Idempotent write: `grep -rniE 'insert into|copy into|append' dags/` — confirm each is paired with a partition-scoped DELETE, MERGE, INSERT OVERWRITE, or `write_disposition=WRITE_TRUNCATE`. Bare INSERT INTO into a retried/backfilled partition is the classic duplicate-on-retry defect. Dagster: confirm delete-then-insert or an idempotent IO manager per partition.
- Catchup/start_date: `grep -rnE 'catchup|start_date|max_active_runs' dags/` — flag `start_date=datetime.now()`/`days_ago` dynamic dates, catchup unset (defaults True pre-3.0) with a far-past start_date, and missing max_active_runs on any catchup=True DAG.
- Retry policy: `grep -rnE 'retries|retry_delay|retry_exponential_backoff|max_retry_delay|execution_timeout' dags/` — cross-reference side-effecting operators (DB writes, API POSTs, file moves). side-effecting + retries>0 + non-idempotent write = double-write; side-effecting + retries=0 = brittle. Every long task needs execution_timeout.
- Trigger-rule/branch: `grep -rnE 'BranchPythonOperator|branch|trigger_rule|ShortCircuit|depends_on_past|wait_for_downstream' dags/` — for every branch followed by a join, verify the join uses `trigger_rule='none_failed_min_one_success'` (default all_success skips the join). Flag depends_on_past/wait_for_downstream that serialize a DAG unintentionally.
- Sensor strategy: `grep -rnE 'Sensor|mode=|poke_interval|timeout=|deferrable' dags/` — flag mode='poke' (default) with long/unbounded waits, missing timeout (defaults to 7 days), poke_interval<60s, and any sensor where deferrable=True/mode='reschedule' is available but unused. Count concurrent poke sensors vs pool/worker slots for starvation.
- Dynamic mapping: `grep -rnE '\.expand\(|\.expand_kwargs\(|map\(|dynamic_partition' dags/` — trace the iterable's source; if runtime XCom/external API of unbounded cardinality, require max_active_tis_per_dag or a pool cap. Flag .expand over large XCom payloads (metastore bloat).
- Cross-DAG: `grep -rnE 'ExternalTaskSensor|ExternalTaskMarker|TriggerDagRunOperator|Dataset|@asset|outlets|schedule=\[' dags/` — for ExternalTaskSensor verify execution_date_fn/execution_delta aligns producer & consumer logical dates (mismatch = permanent hang) and that ExternalTaskMarker exists for clear-propagation; prefer Datasets/Assets per platform standard.
- Secrets/top-level: `grep -rnE 'Variable\.get|Connection\.get|BaseHook\.get_connection|get_variable|os\.environ' dags/` — flag any at module/top level (network+DB call on every parse) vs inside task callables or Jinja `{{ var.value.x }}`. Separately gate and run `gitleaks detect`; fallback `grep -rniE 'password=|token=|secret=|api_key=|aws_secret|-----BEGIN' dags/` for hardcoded creds.
- Top-level cost: scan module scope for heavy imports (pandas/torch/tensorflow), DB queries, file/network IO, or unbounded DAG-generation loops — these run on every scheduler parse. Confirm heavy imports live inside task functions.
- Alerting wiring: confirm on_failure_callback/Notifier (or email_on_failure) on business-critical DAGs; in Airflow 3 confirm `sla=` is removed and replaced with a DeadlineReference/Deadline Alert; flag critical DAGs with no failure routing.
- Pools/concurrency: `grep -rnE 'pool=|max_active_tasks|max_active_runs|priority_weight' dags/` — verify tasks hitting a shared DB/API are assigned a pool sized below the downstream connection/quota limit.
- Render/parse validation (gate each): `command -v airflow` then `airflow dags list-import-errors`; `python -c "import <dag_module>"` (raises AirflowDagCycleException on structural cycles); `airflow tasks render <dag> <task> <logical_date>` to confirm templates resolve; `dagster asset materialize --partition` dry semantics where applicable.

## 4. Blocking bar
Set blocking:true ONLY for (cite file:line + evidence):
- Non-deterministic key path: partition/filename/WHERE derived from now()/today()/random/uuid instead of logical_date/data_interval_start/partition_key — backfill/retry produce wrong or duplicated data.
- Non-idempotent write under retry/backfill: bare INSERT INTO/append into a partition with retries>0 or catchup=True and no DELETE/MERGE/OVERWRITE guard.
- catchup=True (or unset pre-3.0) on a DAG with a far-past static start_date and no max_active_runs cap — cold start floods scheduler/warehouse (DOS).
- start_date=datetime.now()/dynamic — breaks scheduling determinism, prevents runs or causes perpetual catchup.
- Branch-to-join with default trigger_rule all_success — join silently skips on the not-taken branch, dropping downstream with no failure signal.
- ExternalTaskSensor whose execution_delta/execution_date_fn can never align with the producer, or a poke-mode external/long sensor with no timeout — hangs / pins a slot until the 7-day default.
- Hardcoded credential/token/connection string in a DAG file, or Variable.get/Connection/secrets-backend call at top-level parse scope.
- Unbounded .expand() over runtime input with no max_active_tis_per_dag/pool cap — mapped-task explosion.
- Side-effecting task (API POST, external mutation, money movement) with retries>0 but no idempotency key/guard — retry double-applies the side effect.
- Business-critical DAG with no failure alerting (no on_failure_callback/Notifier/email_on_failure) and no deadline/SLA — silent failures.
- Task touching a connection-capped downstream with no pool and max_active_tasks/runs exceeding the downstream limit — saturates shared infra.

Everything else advisory (deferrable-where-poke-but-short, poke_interval<60s, missing execution_timeout on short bounded tasks, heavy top-level imports, missing owner/tags/naming, absent ExternalTaskMarker when alignment is correct, prefer Datasets/Assets, Dagster BackfillPolicy choice, missing exponential backoff, large XCom payloads). A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
Actively look for these negative criteria:
- now()/today() for partition/date logic — the "reads the latest available data" anti-pattern.
- INSERT-without-overwrite into a partition that retries/backfills re-run (duplicate-on-retry).
- catchup left at default + old start_date + no max_active_runs (accidental mass backfill).
- Dynamic start_date (datetime.now()/days_ago at parse).
- Default all_success trigger_rule on a join after a branch (silent skip).
- poke-mode sensor with no/7-day timeout consuming a worker slot (sensor deadlock / worker starvation).
- Variable.get()/Connection lookup or secrets-backend call at top-level DAG scope (network call every parse + leak surface).
- Hardcoded passwords/API keys/connection strings in DAG code.
- Unbounded .expand() over runtime/XCom input with no concurrency cap (mapped-task explosion).
- Retries enabled on a non-idempotent side-effecting task (double-write/double-charge).
- No pool on tasks hammering a connection-limited DB/API.
- Long-running work synchronously occupying a worker instead of a deferrable/triggerer-based operator.
- ExternalTaskSensor with misaligned execution_date and no marker (permanent hang, no clear propagation).
- Storing intermediate files on local worker filesystem between tasks under Celery/K8s executors.
- Critical DAG with no failure callback / no deadline alert (silent failure).
- Heavy compute/DB/network IO in top-level code re-executed on every scheduler parse.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/orchestration-dag-juror.json. ran[]/skipped[] honest. id = `dag-<check>-<file>:<line>`. Nothing outside the JSON.
