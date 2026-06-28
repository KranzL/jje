# Onboarding v3 experiment analysis

Analysis package for the onboarding-v3 holdout experiment. The redesigned
first-run flow is hypothesized to lift seven-day engagement.

## Design

- Unit of randomization: new-account cohort, 50/50 split.
- Primary metric: `d7_active_minutes`, pre-registered with an 80% powered
  sample-size plan at a 3% relative MDE (`analysis/power.py`).
- Secondary metrics: retention, messaging, social, and discovery surfaces
  listed in `analysis/metrics.SECONDARY_METRICS`.

## Decision rule

The ship decision is gated on the primary metric only: it must clear
`p < 0.05` and be adequately powered against the pre-registered effect.
Secondary metrics are confirmed with a Holm step-down across the family
(`analysis/significance.holm`) and reported alongside an exploratory
engagement screen for follow-up hypotheses.

## Usage

```python
from analysis import build_report, plan_primary_metric, render_summary

plan = plan_primary_metric("d7_active_minutes", 20.0, 6.0, mde_relative=0.03)
report = build_report(frame, plan)
print(render_summary(report))
```

## Tests

```
pytest tests/
```
