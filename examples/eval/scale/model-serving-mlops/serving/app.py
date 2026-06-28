from __future__ import annotations

import os
from typing import Mapping

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.schema import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from serving.feature_assembler import assemble_features, order_matches
from serving.registry import ModelBundle, load_bundle

REGISTRY_ROOT = os.environ.get("MODEL_REGISTRY_ROOT", "/srv/models")
PINNED_VERSION = os.environ.get("MODEL_VERSION")

app = FastAPI(title="card-fraud-scorer")

_bundle: ModelBundle | None = None


class ScoreRequest(BaseModel):
    features: Mapping[str, object] = Field(default_factory=dict)
    channel: str = "web"


class ScoreResponse(BaseModel):
    model_version: str
    fraud_probability: float


def _get_bundle() -> ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = load_bundle(REGISTRY_ROOT, PINNED_VERSION)
        if not order_matches(_bundle.stats):
            raise RuntimeError("Serving feature order does not match trained artifact")
    return _bundle


def _validate_payload(payload: Mapping[str, object]) -> None:
    allowed = set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)
    unexpected = set(payload) - allowed
    if unexpected:
        raise HTTPException(
            status_code=422,
            detail=f"unexpected feature keys: {sorted(unexpected)}",
        )


@app.post("/score", response_model=ScoreResponse)
def score(request: ScoreRequest) -> ScoreResponse:
    bundle = _get_bundle()
    _validate_payload(request.features)

    vector = assemble_features(request.features, bundle.stats)
    probability = float(bundle.model.predict_proba([vector])[0][1])

    return ScoreResponse(model_version=bundle.version, fraud_probability=probability)


@app.get("/healthz")
def healthz() -> dict:
    bundle = _get_bundle()
    return {"status": "ok", "model_version": bundle.version}
