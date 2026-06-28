from __future__ import annotations

import pendulum

DAG_ID = "marketing_attribution_daily"
SCHEDULE = "30 4 * * *"
START_DATE = pendulum.datetime(2024, 11, 1, tz="UTC")

SOURCE_BUCKET = "mktg-events-prod"
TOUCHPOINTS_PREFIX = "touchpoints/v3"
CONVERSIONS_PREFIX = "conversions/v2"

WAREHOUSE_CONN_ID = "snowflake_marketing"
S3_CONN_ID = "aws_marketing_lake"
SLACK_CONN_ID = "slack_data_alerts"

STAGING_SCHEMA = "marketing_staging"
MART_SCHEMA = "marketing_mart"

ATTRIBUTION_LOOKBACK_DAYS = 30
SLA_MINUTES = 90

DEFAULT_POOL = "marketing_warehouse_pool"

DEFAULT_ARGS = {
    "owner": "marketing-data-eng",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": pendulum.duration(minutes=30),
    "execution_timeout": pendulum.duration(minutes=45),
    "pool": DEFAULT_POOL,
}

TOUCHPOINT_SOURCES = [
    "paid_search",
    "paid_social",
    "display",
    "email",
    "organic",
    "referral",
]
