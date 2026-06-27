import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger("billing.digest")

BATCH_SIZE = 100
PROVIDER_TIMEOUT = 8.0


@dataclass
class DigestRow:
    id: int
    account_id: str
    period: str
    payload: dict
    attempts: int


class DigestDispatcher:
    def __init__(self, db, provider_url, metrics):
        self._db = db
        self._provider_url = provider_url
        self._metrics = metrics
        self._client = httpx.Client(timeout=PROVIDER_TIMEOUT)

    def _claim_batch(self):
        rows = self._db.query(
            "SELECT id, account_id, period, payload, attempts "
            "FROM billing_digest_outbox "
            "WHERE status = 'pending' "
            "ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED",
            (BATCH_SIZE,),
        )
        return [DigestRow(**r) for r in rows]

    def _mark_sent(self, row, external_id):
        self._db.execute(
            "UPDATE billing_digest_outbox "
            "SET status = 'sent', external_id = %s, sent_at = now() WHERE id = %s",
            (external_id, row.id),
        )

    def run_once(self):
        batch = self._claim_batch()
        if not batch:
            logger.debug("digest outbox empty, nothing to dispatch")
            return 0

        started = time.monotonic()
        sent = 0
        logger.info("dispatching digest batch of %d rows", len(batch))

        for row in batch:
            body = {
                "account": row.account_id,
                "period": row.period,
                "lines": row.payload.get("lines", []),
                "total_cents": row.payload.get("total_cents", 0),
            }
            try:
                resp = self._client.post(
                    f"{self._provider_url}/v2/statements",
                    json=body,
                    headers={"Idempotency-Key": f"{row.account_id}:{row.period}"},
                )
                resp.raise_for_status()
                external_id = resp.json()["id"]
                self._mark_sent(row, external_id)
                self._metrics.increment("digest.dispatched")
                logger.info(
                    "dispatched digest row=%s account=%s external=%s",
                    row.id,
                    row.account_id,
                    external_id,
                )
                sent += 1
            except Exception:
                self._db.execute(
                    "UPDATE billing_digest_outbox SET attempts = attempts + 1 WHERE id = %s",
                    (row.id,),
                )
                continue

        self._db.commit()
        elapsed = time.monotonic() - started
        logger.info(
            "digest dispatch finished sent=%d of %d in %.2fs",
            sent,
            len(batch),
            elapsed,
        )
        self._metrics.timing("digest.batch_seconds", elapsed)
        return sent
