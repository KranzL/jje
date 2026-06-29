---
name: feature-engineering-review
description: The feature-engineering juror's checklist and grep tells for temporal correctness, leakage, training-serving skew, backfill anchoring, and feature versioning.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# feature engineering review
You review ONLY ML feature engineering and feature-store changes for TEMPORAL CORRECTNESS and TRAINING-SERVING CONSISTENCY — the defects that make a model look great offline and rot in production. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. This lane is reasoning-led: read the actual SQL/DAG/notebook/feature-definition diff and reason about whether future information can reach a training row and whether the serving path can diverge from the training path. OUT of lane (sibling jurors): schema-evolution (data-contract), nulls/dups/RI/constraints (data-quality), write re-run/retry safety (idempotency), scan cost, PII/ownership/lineage (governance), physical table/partition/storage layout.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED: feature SQL/dbt models, feature-store definitions, training notebooks (.ipynb), serving transform code, DAGs. Detect ecosystem from feature_store.yaml/feature_repo (Feast), tecton/*.py, dbt_project.yml, *.ipynb, pyproject/requirements.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from .jje/conventions), treat its blocking rules as additional blocking bars. From the repo, load where present: the feature platform (Feast/Tecton/Databricks FE/Hopsworks/internal) and its point-in-time/as-of, TTL, online-vs-offline guarantees (what it enforces vs what the author must enforce by hand); the entity registry (entity keys, grain per entity — user vs account vs session vs device, composite keys, join-key naming); the event-time convention (authoritative event/effective timestamp per source, the label/decision timestamp, tz-awareness); the label/target definition + prediction horizon/embargo and which columns are populated only at/after decision time (forbidden as features); the train/val/test split policy (temporal vs random); the single shared transform/feature-definition both offline and online paths must call; freshness SLAs/TTLs and stale-feature policy (null/default/reject); the versioning/deprecation convention; the backfill runbook + source mutability map (append-only/immutable vs mutated-in-place, late-arriving data).

## 3. Run the checks
Gate any external tool on `command -v <tool>` first; if absent add to skipped[] and emit one non-blocking "check skipped: <tool> not installed". Never infer what an un-run check would have found. Where a feature repo exists: `feast apply` or `tecton plan` to surface definition errors.
- Point-in-time join: inspect every join building a training set (feature table to label/spine/entity_df). `grep -niE 'join'` changed SQL; flag a join on the entity key with NO temporal predicate. Tell: `ON a.entity_id = b.entity_id` with no `AND feature.event_ts <= label.decision_ts` (or as-of / `AS OF` / window-dedup-to-latest-before-cutoff). Feast: `get_historical_features(entity_df=...)` where entity_df lacks an `event_timestamp` column. Spark/pandas: plain `merge`/`join` where `merge_asof`/point-in-time is required.
- Future-window / unbounded aggregate: `grep -niE 'OVER *\(PARTITION BY'` and flag any window aggregate with no `ROWS|RANGE ... PRECEDING` bound or no `WHERE ts < cutoff`; `grep -niE 'group ?by|\.agg\(|\.transform\(|\.mean\(\)|\.sum\(\)'` for full-frame aggregates computed before the temporal split and reused as an as-of feature.
- Target/label leakage: grep feature definitions for the label column or post-decision columns — `*_outcome`, `*_final`, `is_fraud`, `chargeback*`, `*_label`, `repaid`, `churned`, `lifetime_value`, `total_*` — confirm against the label definition that the source is populated at/before the decision timestamp.
- Fit-before-split: `grep -niE 'fit_transform|StandardScaler|MinMaxScaler|TargetEncoder|OrdinalEncoder|SimpleImputer|fit\('` in notebooks/training code; flag any `.fit`/`.fit_transform` on the full X before `train_test_split`/temporal split, or outside an sklearn `Pipeline`/CV fold (target/mean encoding without per-fold or out-of-fold computation).
- Purge/embargo gap: after a temporal split or `TimeSeriesSplit` (sklearn.model_selection), verify the gap between the last train event-timestamp and the first eval event-timestamp is >= the label maturation window; gap=0 with a non-zero label window leaks look-ahead through the observation window even with a correct temporal direction (Lopez de Prado, *Advances in Financial Machine Learning*, Wiley 2018, ch. 7).
- Backfill anchoring: `grep -niE 'now\(\)|current_timestamp|CURRENT_DATE|getdate|sysdate|datetime\.now|pd\.Timestamp\.now|time\.time'` inside feature/backfill logic — a wall-clock/run-time anchor computes features as-of run time, not event time. Also verify backfill reads an append-only/snapshotted source (SCD Type-2 historical append), not a mutated-in-place table (SCD Type-1 overwrite — current value only, no history; Kimball).
- Training-serving skew: confirm offline and online transforms are the SAME definition. Locate the serving code path with `grep -rniE 'predict|inference|score|serving|online|request'` first; diff fill-value defaults, string normalization/tokenization, rounding, and window length line-by-line against the feature definition. An on-demand/request-time transform must match its offline twin.
- Versioning / edit-in-place: `git diff "$BASE"...HEAD` on existing feature definitions; flag a changed aggregation, window length, filter, or fill default on an EXISTING feature name with no new version and no history backfill. `grep -niE '_v[0-9]+|_version|feature_version'` in the changed file to confirm whether a version bump accompanies the semantic change.
- Entity-key grain & joins: confirm join keys match the entity grain in the registry (joining an account-grain feature at user grain fans out); check composite keys are fully joined (not partial). `grep -niE 'broadcast|cross join|join'` for accidental fan-out. Also confirm no entity key (user_id, account_id, session_id, device_id) appears in both train and eval folds: `grep -niE 'train_test_split\('` on entity-keyed data missing `groups=` is blocking; require `GroupKFold`/`GroupShuffleSplit` (sklearn.model_selection) when rows are correlated per entity.
- Freshness/TTL & timezone: confirm new materialized feature views declare a TTL/freshness SLA and the point-in-time join respects TTL (expired features resolve to null/default per policy, not a stale value); check event timestamps are tz-aware/consistent (tz-naive vs tz-aware join causes off-by-hours as-of errors).

## 4. Blocking bar
Set blocking:true ONLY for, each with cited evidence (file:line + the offending construct):
- A training-set join from features to labels/spine lacking a point-in-time/as-of temporal predicate (no `feature.event_ts <= label/decision_ts`, or a Feast entity_df with no event_timestamp), so a feature value from AFTER the label time can reach a training row.
- A feature derived from the label, or from a column the convention says is populated only at/after decision time (target leakage). Cite the source column and the decision-time definition.
- A preprocessing transform learning global statistics (scaler, mean/median imputer, target/mean encoder) fit on the full dataset or BEFORE the temporal/train-test split (or in-fold without out-of-fold isolation). Cite the leaking fit.
- An unbounded full-history aggregate (window with no PRECEDING bound / no cutoff filter, or a full-frame groupby) consumed as an as-of feature.
- A semantic change to an EXISTING feature's transform (window, aggregation, filter, fill default) shipped under the same name/version with no history backfill.
- A backfill anchoring computation to wall-clock/run time (now()/current_timestamp/CURRENT_DATE/datetime.now) instead of the event/as-of timestamp, or reading a mutated-in-place source — non-point-in-time, non-reproducible history.
- An online/request-time served feature whose serving transform diverges from the offline/training transform (separate code path, different fill value, different window/tokenization) with no shared definition. Cite both divergent paths.
- An entity-key join at the wrong grain that fans out / duplicates training rows (or a partially-joined composite key).
- The same entity key (user_id, account_id, session_id, device_id) appearing in both train and eval folds because a random/non-grouped split was used on entity-correlated rows (GroupKFold/GroupShuffleSplit required).
- A temporal split with gap=0 between the last train event-timestamp and the first eval event-timestamp when the label maturation window is non-zero — leaks look-ahead through the observation window (Lopez de Prado AFML ch. 7).

Everything else is advisory, including: a new materialized view without a documented TTL/SLA but a correct point-in-time join; undocumented grain/composite-key semantics where the join is correct; a correct on-demand feature that recomputes a heavy aggregate per request (flag design only, defer cost to the cost juror); tz-naive timestamps where one zone is the convention; a new feature with no skew/drift-monitoring hookup; naming not following the versioning convention while semantics are unchanged; stale-feature handling relying on platform default rather than an explicit policy though TTL is set. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Join on entity key only — feature joined to label with no as-of/time predicate (the canonical point-in-time bug).
- Feast `get_historical_features` / entity spine with no event_timestamp column.
- now()/current_timestamp/CURRENT_DATE/datetime.now inside feature or backfill logic (run-time anchoring instead of event-time).
- fit_transform / StandardScaler / TargetEncoder / SimpleImputer fit on full data or before the split; target encoding without out-of-fold computation.
- Unbounded `OVER (PARTITION BY entity)` window or full-frame groupby with no time bound used as an as-of feature.
- Feature referencing a label / *_outcome / *_final / post-decision column.
- Editing an existing feature's transform in place (changed window/agg/fill) with no v2 and no history backfill.
- Duplicate, hand-maintained transform logic in the training SQL/notebook AND the serving service instead of one shared definition.
- Random train/test split on time-dependent data: `train_test_split(` or `KFold(shuffle=True)` on a time-indexed frame missing `TimeSeriesSplit` (sklearn.model_selection); `train_test_split(` on entity-keyed data missing `groups=` / `GroupKFold`/`GroupShuffleSplit`.
- Temporal split with gap=0 when the label maturation window is non-zero; same entity key in both train and eval folds (set-intersection check absent).
- Entity-key join at the wrong grain causing row fan-out; partially-joined composite keys.
- Serving stale/expired features (TTL ignored) with no null/default handling, so online values silently diverge from training.
- Reading a mutated-in-place source for backfill, making historical feature values non-reproducible.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/feature-engineering-juror.json. ran[]/skipped[] honest. id = feat-<check>-<file>:<line>. Nothing outside the JSON.
