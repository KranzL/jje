import logging
import urllib.request

logger = logging.getLogger("sync_job")

WEBHOOK_URL = "https://billing.internal/api/invoices"


def fetch_invoices(account_id):
    req = urllib.request.Request(f"{WEBHOOK_URL}?account={account_id}")
    resp = urllib.request.urlopen(req, timeout=10)
    payload = resp.read().decode()
    logger.info("fetched invoices for account %s", account_id)
    return payload


def run(account_ids):
    results = {}
    for account_id in account_ids:
        results[account_id] = fetch_invoices(account_id)
    return results
