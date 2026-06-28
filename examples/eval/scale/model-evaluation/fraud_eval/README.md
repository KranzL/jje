# fraud-eval

Offline evaluation harness for the card-fraud scoring model. Consumes a Parquet
file of scored authorizations (`fraud_score`, `is_fraud`, `amount`,
`authorized_at`) and produces a promotion decision for the release pipeline.

## What changed in this PR

Previously the evaluation lived as an ad-hoc notebook. This PR extracts it into a
small package so the release pipeline can call it directly:

- `metrics.py` — threshold-free and threshold-bound metric helpers built on top
  of scikit-learn.
- `thresholds.py` — picks the operating threshold from the **validation** fold
  given a target-precision floor. The held-out test fold is never read here.
- `report.py` — assembles the headline summary plus per-amount-bucket AUC
  breakdown, and applies the promotion gate.
- `run_eval.py` — CLI entry point. Splits the scored frame by time (80/20),
  tunes the threshold on the earlier window, and evaluates on the later one.

## Promotion gate

A model is eligible for promotion when its headline `accuracy` and `roc_auc`
clear the configured floors (defaults `0.985` / `0.90`). Per-segment AUC is
emitted for review but is not part of the automated gate.

## Usage

```bash
python -m fraud_eval.run_eval scored_authorizations.parquet --target-precision 0.6
```
