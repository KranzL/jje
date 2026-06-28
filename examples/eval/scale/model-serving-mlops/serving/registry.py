from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import joblib

from common.schema import MODEL_NAME, FeatureStats


@dataclass(frozen=True)
class ModelBundle:
    version: str
    model: object
    stats: FeatureStats


def _resolve_version(registry_root: str, requested: Optional[str]) -> str:
    if requested and requested != "latest":
        return requested

    pointer_path = os.path.join(registry_root, MODEL_NAME, "PINNED_VERSION")
    if not os.path.exists(pointer_path):
        raise FileNotFoundError(
            f"No pinned version pointer for {MODEL_NAME}; refusing to serve a floating alias"
        )
    with open(pointer_path, encoding="utf-8") as handle:
        pinned = handle.read().strip()
    if not pinned:
        raise ValueError("PINNED_VERSION pointer is empty")
    return pinned


def load_bundle(registry_root: str, requested_version: Optional[str] = None) -> ModelBundle:
    version = _resolve_version(registry_root, requested_version)
    version_dir = os.path.join(registry_root, MODEL_NAME, version)

    model = joblib.load(os.path.join(version_dir, f"{MODEL_NAME}.joblib"))
    with open(os.path.join(version_dir, "feature_stats.json"), encoding="utf-8") as fh:
        stats = FeatureStats.from_dict(json.load(fh))

    return ModelBundle(version=version, model=model, stats=stats)
