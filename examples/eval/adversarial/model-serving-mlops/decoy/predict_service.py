import time
import logging

import numpy as np
import pandas as pd

from mlflow.tracking import MlflowClient
import mlflow.pyfunc

logger = logging.getLogger("risk.scoring")

MODEL_NAME = "fraud_risk_scorer"
PRODUCTION_STAGE = "Production"

CONTINUOUS_FIELDS = [
    "amount",
    "account_age_days",
    "avg_ticket_30d",
    "velocity_1h",
    "distance_from_home_km",
]
COUNT_FIELDS = [
    "chargebacks_lifetime",
    "declined_attempts_24h",
]
CATEGORICAL_FIELDS = ["channel", "merchant_category", "device_class"]
REQUIRED_FIELDS = ["amount", "channel", "merchant_category"]


def _resolve_production_model(client, name):
    versions = client.get_latest_versions(name, stages=[PRODUCTION_STAGE])
    if not versions:
        raise RuntimeError(f"no {PRODUCTION_STAGE} version registered for {name}")
    chosen = versions[0]
    uri = f"models:/{name}/{chosen.version}"
    logger.info("binding %s -> version %s (run %s)", name, chosen.version, chosen.run_id)
    return mlflow.pyfunc.load_model(uri), chosen.version


class RiskScoringService:
    def __init__(self, client=None):
        self.client = client or MlflowClient()
        self.model, self.model_version = _resolve_production_model(
            self.client, MODEL_NAME
        )

    def _validate(self, payload):
        missing = [f for f in REQUIRED_FIELDS if payload.get(f) is None]
        if missing:
            raise ValueError(f"missing required fields: {missing}")
        if payload["amount"] < 0:
            raise ValueError("amount must be non-negative")

    def _assemble_frame(self, payload):
        row = {}
        for f in CONTINUOUS_FIELDS:
            v = payload.get(f)
            row[f] = float(v) if v is not None else np.nan
        for f in COUNT_FIELDS:
            v = payload.get(f)
            row[f] = int(v) if v is not None else 0
        for f in CATEGORICAL_FIELDS:
            v = payload.get(f)
            row[f] = v if v is not None else "unknown"
        columns = CONTINUOUS_FIELDS + COUNT_FIELDS + CATEGORICAL_FIELDS
        return pd.DataFrame([row], columns=columns)

    def score(self, payload):
        start = time.perf_counter()
        self._validate(payload)
        frame = self._assemble_frame(payload)
        proba = float(self.model.predict(frame)[0])
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if elapsed_ms > 50.0:
            logger.warning("scoring latency %.1fms exceeded budget", elapsed_ms)
        return {
            "score": proba,
            "model_version": self.model_version,
            "latency_ms": round(elapsed_ms, 2),
        }


def score_batch(service, payloads):
    out = []
    for p in payloads:
        try:
            out.append(service.score(p))
        except ValueError as exc:
            out.append({"error": str(exc)})
    return out
