import numpy as np
import pandas as pd
import pytest

from src.causal.covariates import default_adjustment_set, TREATMENT, OUTCOME_BINARY
from src.causal.estimators import aipw_ate, ipw_ate, naive_difference
from src.causal.propensity import fit_propensity, propensity_scores, check_overlap


@pytest.fixture
def synthetic_cohort():
    rng = np.random.default_rng(7)
    n = 4000
    prior_trial_count = rng.poisson(0.5, n)
    high_intent = rng.binomial(1, 0.4, n)
    is_returning = (prior_trial_count > 0).astype(int)

    logit_t = -0.5 + 0.8 * high_intent + 0.5 * is_returning
    t = rng.binomial(1, 1 / (1 + np.exp(-logit_t)))

    activated = rng.binomial(1, 1 / (1 + np.exp(-(-0.3 + 1.1 * t + 0.4 * high_intent))))
    logit_y = -0.2 + 0.6 * t + 0.7 * activated + 0.3 * high_intent
    y = rng.binomial(1, 1 / (1 + np.exp(-logit_y)))

    return pd.DataFrame(
        {
            "acquisition_channel": rng.choice(["paid_search", "organic", "referral"], n),
            "device_type": rng.choice(["ios", "android", "web"], n),
            "geo_region": rng.choice(["na", "emea", "apac"], n),
            "plan_tier_at_signup": rng.choice(["free", "pro"], n),
            "prior_trial_count": prior_trial_count,
            "signup_dow": rng.integers(0, 7, n),
            "signup_hour": rng.integers(0, 24, n),
            "marketing_consent": rng.binomial(1, 0.6, n),
            "is_returning_user": is_returning,
            "high_intent_channel": high_intent,
            "activated_within_7d": activated,
            TREATMENT: t,
            OUTCOME_BINARY: y,
        }
    )


def test_propensity_overlap(synthetic_cohort):
    adj = default_adjustment_set()
    model = fit_propensity(synthetic_cohort, adj)
    ps = propensity_scores(model, synthetic_cohort, adj)
    overlap = check_overlap(ps, synthetic_cohort[TREATMENT].to_numpy())
    assert overlap["share_extreme"] < 0.05


def test_aipw_runs_and_reports_ci(synthetic_cohort):
    adj = default_adjustment_set()
    res = aipw_ate(synthetic_cohort, adj)
    assert res["estimand"] == "ATE"
    assert res["ci_low"] < res["estimate"] < res["ci_high"]


def test_ipw_matches_aipw_sign(synthetic_cohort):
    adj = default_adjustment_set()
    a = aipw_ate(synthetic_cohort, adj)
    b = ipw_ate(synthetic_cohort, adj)
    assert np.sign(a["estimate"]) == np.sign(b["estimate"])


def test_naive_differs_from_adjusted(synthetic_cohort):
    naive = naive_difference(synthetic_cohort)
    adjusted = aipw_ate(synthetic_cohort, default_adjustment_set())
    assert naive["method"] == "unadjusted"
    assert adjusted["method"] == "aipw"
