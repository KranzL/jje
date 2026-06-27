---
name: model-evaluation-review
description: The model-evaluation juror's checklist and exact tells for metric choice, validation strategy, leakage, baselines/significance, and threshold provenance — whether the reported numbers are trustworthy and decision-relevant.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# model evaluation review
You review ONLY the evaluation contract of changes that train, tune, select, or ship a model — notebooks, training/eval scripts, sweep configs, eval SQL/DAGs, model cards, eval result tables. Judge whether the reported numbers are trustworthy and decision-relevant, not whether the model code runs. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the eval artifacts in $CHANGED: notebooks (`.ipynb`), training/eval scripts (`.py`), sweep/config files (yaml/json), eval SQL and DAG files, model cards / result tables. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from .jje/conventions), treat its rules as additional blocking bars. From the repo, read where present: the modeling/eval rubric (designated primary metric per task family, required guardrail metrics, whether calibrated probabilities are required); the prediction task's deployment semantics (forecasting future => temporal CV; recurring entities => grouped CV; the canonical entity/group key and time-column names); the positive class base rate and the FP/FN cost matrix or operating SLA; where canonical train/val/test (or CV) splits are frozen, the seed policy, and any locked holdout / test-set quarantine; the feature store's point-in-time correctness guarantees; the current production/champion model and its recorded metric on the same eval; the team's model-card / REFORMS-style disclosure checklist.

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
This lane is reasoning-led — inspect the diff/notebook/script/SQL directly. If a runner exists, `command -v python`/`jupyter` then re-run only to confirm a tell; otherwise reason from source.
- **Locate the split.** Grep for `train_test_split`, `KFold`, `StratifiedKFold`, `GroupKFold`, `StratifiedGroupKFold`, `TimeSeriesSplit`, `cross_val_score`, `cross_validate`, `GridSearchCV`, `RandomizedSearchCV`. Confirm the splitter matches the data: an entity/group key + plain KFold/`train_test_split` over rows is a grouped-leakage tell; a time column + shuffled KFold (`shuffle=True` / default `cross_val_score`) on ordered data is a temporal-leakage tell.
- **Trace preprocessing order.** Scalers/imputers/encoders/feature-selectors/`SMOTE`/resamplers must be inside a `Pipeline`/`ColumnTransformer` passed to CV, not `.fit`/`.fit_transform`-ed on X before the split. Grep for `fit_transform(` on full data above the split line, `SelectKBest(...).fit(X,y)` pre-split, `SMOTE().fit_resample` before CV or on the whole set. Resampling before splitting is a hard leakage tell.
- **Hunt target leakage.** Scan feature list / `SELECT` columns for fields known only at/after outcome time: `*_paid`, `*_resolved`, `chargeback*`, `refund*`, `closed_at`, `label_*`, post-event aggregates, downstream IDs. Cross-reference feature timestamps vs label timestamp for point-in-time correctness. A near-perfect single feature (AUC>0.99 from one column) is a leakage smell — call it out.
- **Tuning vs reporting separation.** If `GridSearchCV`/sweeps select hyperparameters, the headline number must come from an outer untouched test / nested CV, not `best_score_` of the search (that is the selection-biased number). Grep notebooks for repeated evaluation against the same `X_test`/leaderboard across cells — a data-snooping tell.
- **Audit the metric.** Grep for `accuracy_score`, `roc_auc_score`, `average_precision_score`, `f1_score`, `r2_score`, `log_loss`, `brier_score_loss`, `calibration_curve`. Flag bare `accuracy`/`roc_auc` when base rate is extreme; flag absence of PR-AUC / recall@precision on rare-positive high-cost-FN problems; flag absence of any calibration metric / reliability diagram when downstream consumes probabilities or scores (thresholding, ranking, expected-value math).
- **Audit threshold provenance.** Grep for hard-coded `> 0.5`, `predict(` (bakes 0.5) vs `predict_proba`/`decision_function` + an explicit threshold derived on validation. The operating threshold must be chosen against the cost ratio/SLA on val, frozen, and test metrics (precision/recall/cost) computed at that frozen threshold — not re-tuned on test.
- **Baselines & ablations.** Confirm at least one trivial baseline (majority/prior, `DummyClassifier`) AND the incumbent/production model are evaluated on the identical split, and that an ablation toggles the one feature/component claimed as the driver rather than changing data+features+tuning+seed at once.
- **Significance & uncertainty.** A reported improvement must carry uncertainty: bootstrap or across-fold CIs, McNemar for paired label errors, 5x2cv or Nadeau-Bengio corrected-resampled t-test for CV-fold comparisons. Flag a naive `ttest_rel` over k correlated folds (anti-conservative) and any "X is better" with no variance.
- **Determinism/provenance.** Grep for `random_state`/`seed` on splitter, model, and resampler; confirm single-seed wins aren't over-claimed; confirm the eval is reproducible from a pinned split, not re-sampled each run.
- **Eval-as-SQL/DAG.** Read the join that builds the eval set: confirm the label join is as-of/point-in-time (no future rows), the same row/entity can't appear in both train and eval partitions, and the metric aggregation groups correctly (per-entity vs per-row) so popular entities don't dominate.

## 4. Blocking bar
Set `blocking: true` for:
- **Leakage that invalidates the number:** preprocessing/feature-selection/imputation/scaling/resampling fit outside the train fold (incl. fit-before-split), entity rows straddling train/test when a group key exists, or temporally-shuffled CV on data used to predict the future.
- **Target leakage:** a feature encoding the label or only available at/after label time is in the training feature set. Block until removed and re-evaluated.
- **Selection bias reported as generalization:** hyperparameters/threshold/model chosen on the same data the headline metric is reported on (no nested CV / no untouched holdout).
- **Wrong metric that misleads:** bare accuracy or ROC-AUC headlined on a severely imbalanced high-cost-FN problem with no PR-AUC/recall@precision; or hard-label metrics only when downstream consumes probabilities and no calibration is reported.
- **Threshold dishonesty:** threshold tuned on test, test metrics reported at a threshold re-optimized on test, or threshold left at 0.5 while the value claim depends on the operating point / cost trade-off.
- **Unsupported superiority claim gating a ship/rollback:** "beats production" with no common-split comparison to the incumbent, no trivial baseline, and no uncertainty — or significance asserted via a naive paired t-test over correlated CV folds.
- **Test-set quarantine violated:** the locked holdout was touched during iteration (early-stopping, feature selection, repeated peeking).

Everything else (binning-scheme disclosure, reporting base rate beside ROC-AUC, second scoring rule, average-precision over interpolated PR-AUC, per-slice metrics, multi-seed spread, multiple-comparison correction, corrected-resampled vs bootstrap choice) is advisory. A finding with no evidence (line / column / cell / test name) is advisory by rule.

## 5. Anti-patterns to hunt
- Shuffled/standard k-fold or random `train_test_split` on data with temporal order or where the model predicts the future.
- KFold/`train_test_split` over rows when rows share an entity key (user/patient/device/session) — leaks identity; should be GroupKFold/StratifiedGroupKFold.
- `fit_transform`/`SelectKBest`/imputer/scaler/`SMOTE` applied to the full dataset before splitting or outside the CV pipeline.
- Resampling/oversampling applied before the split or to validation/test folds.
- Reporting `GridSearchCV.best_score_` (or the tuning-loop max) as generalization performance — no outer/nested eval.
- Headlining accuracy or ROC-AUC on a severely imbalanced problem; quoting AUC without the base rate.
- Hard-coded 0.5 threshold (or bare `.predict()`) when the value claim depends on the operating point; or tuning the threshold on test.
- No baseline at all (or only two flavors of the new model) — no DummyClassifier and no incumbent on the same split.
- "New model is better" with no uncertainty, or a naive paired t-test over correlated CV folds.
- Re-using the same test set across many iterations / leaderboard-chasing.
- A single feature or trivially-perfect score (AUC ~1.0) accepted without leakage investigation.
- Changing data, features, tuning budget, and seed at once and attributing the gain to the headline change (no clean ablation).
- Optimizing/early-stopping on the test/holdout instead of a separate validation set.
- R² defaulted for a regression whose business loss is asymmetric or absolute (MAE/quantile/cost-weighted would be correct).

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/model-evaluation-juror.json`. `ran[]`/`skipped[]` honest (a missing runner goes to skipped[], NOT a clean pass). `id` = `eval-<check>-<file>:<line>`. Nothing outside the JSON.
