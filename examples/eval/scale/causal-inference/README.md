# Onboarding Call Effect Analysis

Estimates the effect of receiving an onboarding call shortly after signup on
90-day retention.

## Estimand

ATE of `received_onboarding_call` on `retained_90d` in the signup cohort.
Identification is by conditional ignorability given baseline (pre-signup and
signup-time) characteristics, with overlap enforced via propensity trimming.

## Pipeline

1. `data.build_analysis_frame` assembles the cohort, derives the treatment
   indicator from the call timestamp, and builds features.
2. `propensity.fit_propensity` fits the treatment model and `check_overlap`
   validates positivity.
3. `estimators.aipw_ate` produces the doubly-robust point estimate and CI;
   `ipw_ate` and `naive_difference` are provided as cross-checks.

## Mediation

`mediation.estimate_natural_effects` decomposes the total effect into the part
flowing through early product activation (`activated_within_7d`) and the part
that does not. This is reported alongside the ATE for interpretation only; the
two analyses answer different questions.

## Adjustment set

Baseline covariates are declared in `covariates.py`. Channel, device, region,
and plan tier are one-hot encoded; trial history and signup-timing features are
scaled. The set is intended to capture common causes of both the call routing
and downstream retention.
