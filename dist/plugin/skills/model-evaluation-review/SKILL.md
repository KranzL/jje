---
name: model-evaluation-review
description: The model-evaluation juror's checklist and exact tells for metric choice, validation strategy, baselines/significance, and threshold provenance — whether the reported numbers are trustworthy and decision-relevant.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# model evaluation review
You review ONLY the evaluation contract of changes that train, tune, select, or ship a model — notebooks, training/eval scripts, sweep configs, eval SQL/DAGs, model cards, eval result tables. Judge whether the reported numbers are trustworthy and decision-relevant. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the eval artifacts in $CHANGED: notebooks (`.ipynb`), training/eval scripts (`.py`), sweep/config files (yaml/json), eval SQL and DAG files, model cards / result tables. Review only those.

## 2. Context to load
Load where present: the task family's designated primary metric and required guardrail metrics; whether calibrated probabilities are required downstream (ranking, thresholding, expected-value); the positive class base rate and FP/FN cost matrix; the CV splitter standard, grouping key, time column, and label maturation window W (window between feature cutoff and label realization — determines required purge gap); the frozen holdout/test-set quarantine policy and seed policy; the incumbent/champion metric on the same eval.

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
- **Split.** Grep `TimeSeriesSplit`, `KFold`, `StratifiedKFold`, `GroupKFold`, `StratifiedGroupKFold`, `train_test_split`, `cross_val_score`. Flag shuffled KFold/`train_test_split` on time-ordered data. Flag `KFold` without `groups=` when an entity key exists. Flag `TimeSeriesSplit(` with no `gap=` argument when W > 0 — sklearn's default `gap=0` places test rows within the maturation window (look-ahead bug); require `gap >= W` or explicit documentation that W = 0.
- **Tuning/reporting separation.** `GridSearchCV.best_score_` or sweep max is selection-biased; headline must come from an outer untouched holdout or nested CV. Grep notebooks for repeated evaluation against the same `X_test` across cells (leaderboard-chasing).
- **Metric audit.** Ground metric choice in proper scoring rules: Brier score and log_loss are strictly proper (each is optimised at the true probability); accuracy is not a proper scoring rule. Grep `accuracy_score`, `roc_auc_score`, `average_precision_score`, `log_loss`, `brier_score_loss`. Flag bare accuracy or ROC-AUC when positive rate <= 5% — a majority-class baseline achieves >= 95% accuracy at that base rate, making accuracy actively misleading. Flag absence of AUPRC/recall@precision on rare-positive high-cost-FN tasks (Davis & Goadrich 2006 establishes AUPRC's superiority over AUROC under imbalance). Flag absence of a calibration metric when downstream consumes probabilities: ECE (Expected Calibration Error, Guo et al. 2017) or Brier score is the named standard.
- **Threshold provenance.** Grep `> 0.5`, `.predict(` (bakes 0.5). The operating threshold must be derived on validation against the cost ratio/SLA, frozen, and test metrics computed at that frozen threshold — not re-tuned on test.
- **Baselines.** At least one trivial baseline (`DummyClassifier`, majority/prior) AND the incumbent on the identical split. An ablation must toggle the single claimed-driver feature/component, not change data + features + tuning + seed simultaneously.
- **Significance/uncertainty.** Reported improvements must carry uncertainty: bootstrap CIs (B >= 1000 for stable percentile CIs), McNemar for paired label errors, or Nadeau-Bengio corrected-resampled t-test for CV comparisons. Flag naive `ttest_rel` over k correlated folds (anti-conservative). Flag "X is better" with no variance reported.
- **Determinism.** Grep `random_state`/`seed` on splitter, model, resampler; flag single-seed wins over-claimed without multi-seed spread.
- **Eval SQL/DAG.** Check that partition filters do not silently shrink or skew the eval population. Flag label staleness when the pipeline runs on a delay that shifts the label window.
- **Prediction intervals.** When the model outputs quantile or interval predictions, verify empirical coverage matches nominal level (a 90% PI achieving 60% empirical coverage is an eval failure).

## 4. Blocking bar
Set blocking:true (with cited evidence — file:line, metric value, specific grep tell) ONLY for:
- **Selection bias as generalization:** headline metric is `best_score_` / tuning-loop max with no nested CV or untouched holdout.
- **Wrong metric misleads:** bare accuracy or ROC-AUC headlined at positive rate <= 5% with no AUPRC/recall@precision (Davis & Goadrich 2006); absence of any calibration metric (ECE, Brier score, log_loss per Guo et al. 2017) when downstream consumes probabilities for ranking, thresholding, or expected-value computation.
- **Threshold dishonesty:** threshold tuned on test data, or left at 0.5 while the value claim depends on the operating point / cost trade-off.
- **Unsupported superiority claim gating ship/rollback:** "beats production" with no common-split incumbent comparison, no trivial baseline, no uncertainty; or significance asserted via naive `ttest_rel` over correlated CV folds.
- **Test-set quarantine violated:** locked holdout touched during iteration, feature selection, or early-stopping.
- **Temporal purge absent:** `TimeSeriesSplit(gap=0)` (sklearn default) when label maturation window W > 0 — test rows fall within the maturation window, invalidating the reported metric.
Everything else is advisory. A finding with no cited evidence (file:line, metric value, grep tell) is advisory by rule.

## 5. Anti-patterns to hunt
- Shuffled KFold or random `train_test_split` on time-ordered data (look-ahead bias).
- `KFold`/`train_test_split` without `groups=` when rows share an entity key — entity memorization.
- `GridSearchCV.best_score_` or sweep max reported as generalization — no outer/nested eval.
- Bare accuracy or ROC-AUC headlined at positive rate <= 5%; AUC quoted without the base rate.
- No calibration metric (ECE, Brier, log_loss) when probabilities drive downstream decisions.
- Hard-coded 0.5 threshold / bare `.predict()` when the value claim depends on the cost trade-off; threshold re-tuned on test.
- No `DummyClassifier` / trivial baseline and no incumbent on the same split.
- "New model is better" with no uncertainty, or naive `ttest_rel` over correlated CV folds.
- Test set reused across many iterations / leaderboard-chasing.
- `TimeSeriesSplit(gap=0)` when label maturation window W > 0.
- Partition filter silently shrinking or skewing the eval population.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/model-evaluation-juror.json`. `ran[]`/`skipped[]` honest (a missing runner goes to skipped[], NOT a clean pass). `id` = `eval-<check>-<file>:<line>`. Nothing outside the JSON.
