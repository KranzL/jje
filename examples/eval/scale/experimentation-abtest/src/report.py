from __future__ import annotations

import yaml

from . import metrics
from .cuped import apply_cuped, variance_reduction
from .loaders import build_frame
from .sequential import evaluate_look
from .srm import sample_ratio_mismatch
from .variance import (
    clustered_ratio_estimate,
    difference_test,
    estimate_for,
)


def _load_config(path: str) -> dict:
    with open(path) as handle:
        return yaml.safe_load(handle)


def _metric_block(config: dict, frame, alpha: float) -> dict:
    builders = {
        "checkout_starts_per_user": (metrics.checkout_starts_per_user, frame.users),
        "add_to_cart_rate": (metrics.add_to_cart_rate, frame.users),
        "revenue_per_session": (metrics.revenue_per_session, frame.sessions),
    }

    results = {}
    for name, (builder, source) in builders.items():
        control = builder(source, "control")
        treatment = builder(source, "treatment")
        est_c = estimate_for(control)
        est_t = estimate_for(treatment)
        test = difference_test(est_c, est_t, alpha)
        results[name] = {
            "control": est_c.point,
            "treatment": est_t.point,
            "relative_lift": metrics.relative_lift(control, treatment),
            **test,
        }
    return results


def _primary_robustness(frame, alpha: float) -> dict:
    out = {}
    for variant in ("control", "treatment"):
        rows = frame.sessions[frame.sessions["variant"] == variant]
        out[variant] = clustered_ratio_estimate(
            numerator=rows["checkout_starts"].to_numpy(dtype=float),
            denominator=rows["session_id"].notna().to_numpy(dtype=float),
            cluster_id=rows["user_id"].to_numpy(),
            name="checkout_starts_per_session_clustered",
        )
    diff = difference_test(out["control"], out["treatment"], alpha)
    return diff


def run(config_path: str, exposures_path: str, sessions_path: str) -> dict:
    config = _load_config(config_path)
    alpha = config["analysis"]["alpha"]
    salt = config["assignment_salt"]

    frame = build_frame(exposures_path, sessions_path, salt)

    weights = {v["name"]: v["weight"] for v in config["variants"]}
    srm = sample_ratio_mismatch(frame.exposures, weights)

    users_cuped = apply_cuped(frame.users, "pre_period_checkout_starts_per_user")
    vr = variance_reduction(frame.users, "pre_period_checkout_starts_per_user")

    metric_results = _metric_block(config, frame, alpha)

    schedule = config["analysis"]["looks"]["schedule"]
    primary_z = metric_results["checkout_starts_per_user"]["z"]
    look = evaluate_look(primary_z, len(schedule) - 1, schedule, alpha)

    return {
        "srm": srm,
        "cuped_expected_variance_reduction": vr,
        "cuped_rows": len(users_cuped),
        "metrics": metric_results,
        "primary_robustness": _primary_robustness(frame, alpha),
        "primary_sequential_look": look,
    }
