---
name: data-leakage-review
description: The data-leakage juror's checklist and exact tells for any path that lets a model see eval/test or future information at fit/selection/tuning time.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# data leakage review
You review ONLY ML data leakage: any path that lets a model see data at fit/selection/tuning time it would not have at the prediction-time decision boundary. PRINCIPAL level — reconstruct the temporal/causal order of each feature relative to the label timestamp and the split. Do not surface lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the relevant artifacts: training/eval scripts, feature-engineering and dataset-construction code (pandas/Spark/SQL), notebooks (.ipynb), dbt/SQL feature models, feature-store definitions (Feast/Tecton/SageMaker FS/Databricks FS), CV/split code, DAG files. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from .jje/conventions), treat its blocking rules as additional blocking bars. Then read from the repo where present:
- The prediction-time contract: WHAT is known at the decision/cutoff timestamp and WHEN, vs what becomes known only after. This is the single most important input — without it legitimate vs leaky features cannot be distinguished.
- The label definition and its observation/maturation window: how y is computed, from which columns, over what window, and the lag between feature cutoff and label realization.
- The team's splitting standard: random vs temporal vs grouped; the grouping key(s) defining an entity that must not cross splits (user_id, account_id, patient_id, session_id, device_id, document_id); the holdout/backtest protocol.
- The feature platform and whether point-in-time / as-of joins are mandated for time-dependent features.
- The offline-eval protocol: which dataset is the sacrosanct test set, how many iterations touched it, whether nested CV is standard, the expected CV splitter.
- The feature catalog/lineage: source-table update semantics (Type-1 overwrite vs Type-2 historical; mutable/backfilled columns).
- The resampling/class-imbalance policy (where SMOTE/over/undersampling/augmentation may run relative to the split).
- Known banned/illegitimate features and prior leakage incidents for this domain.

## 3. Run the checks (gate every external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
This lane is mostly reasoning over the diff/SQL/notebook. Be specific:
- Reconstruct feature-vs-label timing for every NEW/changed feature: "is this value knowable as of the decision timestamp?" Inspect the SQL/Spark/pandas building it for joins to tables mutated after the event, aggregates with no time upper bound, and any column populated by the outcome.
- Grep the preprocessing-before-split tell: `fit_transform(` or `.fit(` on X/full data BEFORE `train_test_split`/`GroupKFold`/`TimeSeriesSplit`. Confirm test data is only `.transform(`-ed with a train-fitted object. Tells: `SelectKBest(...).fit_transform(X, y)` then split; `StandardScaler().fit(X)`; `scaler.fit_transform(X_test)`.
- Verify preprocessing lives INSIDE the CV loop / a `Pipeline`/`ColumnTransformer` passed to `cross_val_score`/`GridSearchCV`. A scaler/imputer/encoder/PCA/feature-selector fit outside `cross_val_*` is leakage even with a correct outer split.
- Check the CV splitter matches the data: time-ordered -> `TimeSeriesSplit`/blocked/purged-embargo (not `KFold`/`shuffle=True`); entity-correlated -> `GroupKFold`/`StratifiedGroupKFold`/`GroupShuffleSplit` with correct `groups=`. Grep `KFold`, `train_test_split(` without `stratify`/`groups`, `shuffle=True` on temporal data.
- Hunt target/mean/WOE/count/leave-one-out encoders: `TargetEncoder`, `category_encoders`, `.map(group_means)`, `groupby(...).agg(...).merge(...)` consuming y. Require out-of-fold (CV-aware Pipeline, `cv=` wrappers, k-fold OOF). Anti-pattern: target means on the whole frame then merged back.
- Check split-then-leak ordering of resampling/augmentation: `SMOTE`, `RandomOverSampler`, `resample`, image augmentation, `drop_duplicates`-after-augment must run only on the training fold.
- Detect duplicate/near-duplicate cross-split contamination: joins/concats that place the same primary key in train and eval; dedup before vs after split; for grouped data confirm no entity key appears in two splits (presence/absence of a `set(train.group) & set(test.group)` check).
- Audit feature-store / training-set construction: confirm point-in-time / as-of joins with an event-timestamp cutoff for every time-dependent feature; flag naive `JOIN ... ON entity_id` to the LATEST value, `MAX(ts)` without `<= label_ts`, or `last_30d` windows not anchored to the label timestamp.
- Inspect label-feature window overlap in SQL: feature aggregation window and label observation window must not intersect; grep `BETWEEN` clauses and window frames for cutoffs extending past the decision time.
- Empirical smell test where feasible: a single feature with near-perfect AUC/importance, accuracy collapsing from ~0.99 offline to chance on a true temporal holdout, perfect scores on hard data, or an implausibly dominant SHAP/importance feature (proxy-for-target tell).
- Check model-selection hygiene: a held-out test set tuning/feature-selection never touched? Flag GridSearch/feature-selection reporting test-fold scores, missing nested CV, and a test set reused across many iterations (peeking).
- Verify training/serving parity for the *cause* of skew: a feature trivially available offline but not computable as-of the request at serving time is leakage; confirm the serving pipeline can produce each feature from only as-of-request inputs.

For notebooks, inspect `.ipynb` cell source (e.g. `jq -r '.cells[].source[]' nb.ipynb` if `command -v jq`) for the same tells; cell execution order can hide a before-split fit.

## 4. Blocking bar
Set blocking:true (with cited evidence — file:line, the SQL clause, the failing protocol) ONLY for:
- Any preprocessing/feature-selection/imputation/scaling/encoding/dimensionality-reduction/vocabulary/embedding/resampling step fit on data that includes eval or test rows (before-split, or outside the CV loop). Contaminates the metric and model selection.
- A feature that is a function of the label, a deterministic proxy for it, or a post-outcome artifact populated only after the predicted event. One such feature invalidates the model.
- Temporal/look-ahead leakage on time-dependent data: a feature uses information dated after the decision timestamp (naive latest-value join, unbounded aggregate, feature/label window overlap), OR time-ordered data split/CV'd with random shuffling.
- Group/entity leakage: correlated rows from the same entity cross the train/eval boundary because a random split was used where the grouping key demanded GroupKFold/temporal split.
- Target/mean/WOE/count/LOO encoding (or any label-informed transform/selection) computed on full data or without out-of-fold isolation, when its output feeds the eval set.
- Duplicate or augmented/oversampled copies of the same record in both train and eval (augmentation/SMOTE/bootstrap before the split, or dedup skipped against a known duplicate source).
- Improper CV that lets model selection see the test fold: missing nested CV when tuning, the sacrosanct test set reused across iterations, or a structurally wrong splitter (KFold on time series, plain KFold on grouped data).
- A reported headline metric produced by any pipeline exhibiting the above — the number on the PR/model card is untrustworthy and must be regenerated under a clean protocol before merge.
Everything else is advisory: no never-touched final holdout though CV is otherwise correct; hand-wired preprocessing that is correct but leakage-prone to future edits (recommend Pipeline/ColumnTransformer); TimeSeriesSplit without purge/embargo gap under a maturation window; no model info sheet / leakage checklist; a dominant-but-plausible feature unverified (recommend ablation + temporal holdout); asserted-but-untested train/serving parity; possible test-set sampling bias that does not cross the eval boundary. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `fit_transform`/`fit` on full X (scaler, imputer, encoder, PCA, SelectKBest, vectorizer) BEFORE `train_test_split`, or fit once outside the cross_val loop.
- `.fit()`/`.fit_transform()` on the test/validation set instead of `.transform()` with a train-fitted object.
- `train_test_split`/`KFold(shuffle=True)` on data with a time index, or any random split where rows are time-ordered (look-ahead bias).
- Random split where multiple rows share an entity key (user/patient/account/session/device/document) — entity memorization instead of GroupKFold/StratifiedGroupKFold.
- Target/mean/WOE/count/LOO encoding computed over the whole dataset or merged from a global groupby instead of out-of-fold / CV-internal.
- SMOTE/oversampling/undersampling/augmentation/bootstrap applied before the split, duplicating neighbors across train and eval.
- Features that are proxies for or deterministic functions of the label (predict YearlyCharge from MonthlyCharge; a status/reason/closed_at column set only after the outcome).
- Naive feature-store/SQL join to the LATEST value (`MAX(ts)`, current dimension row) with no `<= decision_timestamp` as-of cutoff; aggregate windows not anchored to label time.
- Feature aggregation window overlapping the label observation window (the feature "sees" part of the outcome period).
- Hyperparameter tuning / feature selection reporting test-fold scores; no nested CV; reusing the single test set across many iterations (adaptive overfitting).
- Imputation/normalization statistics, embeddings, or vocabularies computed on train+test combined.
- Deduplication performed after the split (or not at all) so identical/near-identical rows land in both train and eval.
- Using future-revised / backfilled dimension attributes (Type-1 overwritten values) as if known at event time.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/data-leakage-juror.json. ran[]/skipped[] honest. id = leak-<check>-<file>:<line>. Nothing outside the JSON.
