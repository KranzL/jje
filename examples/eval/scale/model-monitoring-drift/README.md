# Drift Monitoring Service

Daily drift monitoring for production scoring models. The service compares a
recent serving window against a lagged baseline window and raises alerts when a
monitored surface moves beyond its configured threshold.

## Coverage

The monitor provides full drift-surface coverage for every registered model:

- **Feature drift** — per-feature PSI for numeric inputs and Jensen-Shannon
  divergence for categorical inputs.
- **Prediction drift** — score-distribution PSI plus positive-rate shift at the
  decision threshold.
- **Concept drift** — relationship change between inputs and outcomes.
- **Performance drift** — degradation of the live model against ground truth.

`DriftReport.summary()` reports the set of surfaces monitored on each run so
downstream dashboards can assert that no surface was skipped.

## Baselines and label lag

Ground-truth labels for this model arrive roughly seven days after scoring, so
the baseline window is anchored `label_lag_days` behind `as_of`. This keeps the
reference window aligned to a fully settled period and avoids comparing the live
window against partially-populated history.

## Configuration

See `config/monitoring.yaml`. Thresholds were calibrated from a six-month
backtest; PSI of 0.2 is treated as the actionable boundary for both feature and
score distributions.

## Running

Build a `MonitorConfig` from `config/monitoring.yaml`, construct a
`DriftMonitor` with an `AlertSink`, and call `run(history, as_of)`. The returned
`DriftReport.summary()` is what dashboards and the daily job assert against.
