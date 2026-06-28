from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.metrics import PRIMARY_METRIC, SECONDARY_METRICS, relative_lift, winsorize
from analysis.power import plan_primary_metric, sample_size_per_arm
from analysis.significance import benjamini_hochberg, bonferroni, holm, welch_ttest


@pytest.fixture
def experiment_frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 800
    rows = []
    for arm, shift in [("control", 0.0), ("treatment", 0.6)]:
        block = {"arm": [arm] * n, PRIMARY_METRIC: rng.normal(20 + shift, 6, n)}
        for metric in SECONDARY_METRICS:
            block[metric] = rng.normal(5, 2, n)
        rows.append(pd.DataFrame(block))
    return pd.concat(rows, ignore_index=True)


def test_relative_lift_zero_base():
    assert np.isnan(relative_lift(np.array([1.0]), np.array([0.0])))


def test_winsorize_caps_tail():
    values = np.array([1.0, 2.0, 3.0, 100.0])
    capped = winsorize(values, limit=0.75)
    assert capped.max() < 100.0


def test_sample_size_monotonic_in_effect():
    small = sample_size_per_arm(6.0, 0.3)
    large = sample_size_per_arm(6.0, 1.2)
    assert small > large


def test_plan_primary_metric_fields():
    plan = plan_primary_metric(PRIMARY_METRIC, 20.0, 6.0, mde_relative=0.03)
    assert plan.required_per_arm > 0
    assert plan.power == 0.8


def test_bonferroni_scales_with_count():
    raw = [0.01, 0.02, 0.04]
    adjusted = bonferroni(raw)
    assert adjusted[0] == pytest.approx(0.03)


def test_bh_and_holm_agree_on_strong_signal():
    p = [0.0001, 0.6, 0.7, 0.8]
    assert benjamini_hochberg(p)[0]
    assert holm(p)[0]


def test_welch_detects_primary_shift(experiment_frame):
    t = experiment_frame.loc[experiment_frame.arm == "treatment", PRIMARY_METRIC]
    c = experiment_frame.loc[experiment_frame.arm == "control", PRIMARY_METRIC]
    result = welch_ttest(t.to_numpy(), c.to_numpy())
    assert result.p_value < 0.05
    assert result.estimate > 0
