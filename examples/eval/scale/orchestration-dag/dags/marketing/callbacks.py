from __future__ import annotations

from typing import Any

import pendulum
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

from marketing.config import SLACK_CONN_ID


def _format_alert(context: dict[str, Any], status: str) -> str:
    ti = context["task_instance"]
    fired_at = pendulum.now("UTC").to_datetime_string()
    return (
        f"[{status}] {ti.dag_id}.{ti.task_id}\n"
        f"logical_date={context['ds']} run_id={context['run_id']}\n"
        f"try={ti.try_number} alerted_at={fired_at}\n"
        f"log_url={ti.log_url}"
    )


def notify_failure(context: dict[str, Any]) -> None:
    hook = SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID)
    hook.send(text=_format_alert(context, "FAILED"))


def notify_sla_miss(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    hook = SlackWebhookHook(slack_webhook_conn_id=SLACK_CONN_ID)
    missed = ", ".join(sorted({s.task_id for s in slas}))
    hook.send(text=f"[SLA MISS] {dag.dag_id} tasks={missed}")
