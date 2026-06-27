import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger("integrations.webhook")

BATCH_SIZE = 100
DELIVER_TIMEOUT = 8.0


@dataclass
class WebhookRow:
    id: int
    subscription_id: str
    event_type: str
    payload: dict
    attempts: int


class WebhookReplayer:
    def __init__(self, db, metrics):
        self._db = db
        self._metrics = metrics
        self._client = httpx.Client(timeout=DELIVER_TIMEOUT)

    def _claim_batch(self):
        rows = self._db.query(
            "SELECT id, subscription_id, event_type, payload, attempts "
            "FROM webhook_outbox "
            "WHERE status = 'pending' AND next_attempt_at <= now() "
            "ORDER BY next_attempt_at LIMIT %s FOR UPDATE SKIP LOCKED",
            (BATCH_SIZE,),
        )
        return [WebhookRow(**r) for r in rows]

    def _endpoint_for(self, subscription_id):
        row = self._db.query_one(
            "SELECT target_url FROM webhook_subscriptions WHERE id = %s",
            (subscription_id,),
        )
        return row["target_url"]

    def _mark_delivered(self, row):
        self._db.execute(
            "UPDATE webhook_outbox SET status = 'delivered', delivered_at = now() "
            "WHERE id = %s",
            (row.id,),
        )

    def _reschedule(self, row):
        backoff = min(3600, 2 ** row.attempts * 30)
        self._db.execute(
            "UPDATE webhook_outbox "
            "SET attempts = attempts + 1, "
            "next_attempt_at = now() + (%s || ' seconds')::interval, "
            "status = CASE WHEN attempts + 1 >= 8 THEN 'dead' ELSE 'pending' END "
            "WHERE id = %s",
            (backoff, row.id),
        )

    def run_once(self):
        batch = self._claim_batch()
        if not batch:
            return 0

        started = time.monotonic()
        delivered = 0
        logger.info("replaying webhook batch of %d rows", len(batch))

        for row in batch:
            endpoint = self._endpoint_for(row.subscription_id)
            envelope = {
                "type": row.event_type,
                "data": row.payload,
                "delivery": row.attempts + 1,
            }
            try:
                resp = self._client.post(endpoint, json=envelope)
                resp.raise_for_status()
                self._mark_delivered(row)
                self._metrics.increment("webhook.delivered")
                logger.info(
                    "delivered webhook row=%s sub=%s type=%s",
                    row.id,
                    row.subscription_id,
                    row.event_type,
                )
                delivered += 1
            except Exception:
                logger.exception(
                    "webhook delivery failed row=%s sub=%s attempt=%d",
                    row.id,
                    row.subscription_id,
                    row.attempts + 1,
                )
                self._metrics.increment("webhook.failed")
                self._reschedule(row)
                continue

        self._db.commit()
        elapsed = time.monotonic() - started
        logger.info(
            "webhook replay finished delivered=%d of %d in %.2fs",
            delivered,
            len(batch),
            elapsed,
        )
        return delivered
