---
name: model-monitoring-drift-review
description: The model-monitoring-drift juror's checklist and grep tells for drift-surface coverage, method/type fit, ground-truth-lag, alerting/retraining economics, and segment/feedback dynamics.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# model monitoring & drift review
You review ONLY the runtime behavior of a deployed model: the statistical machinery that watches a live model's inputs, outputs, and realized quality over time, and the logic turning those signals into alerts and retraining. PRINCIPAL level — hold the bar at what a principal engineer would block, not surface lint. This is deliberately NOT at-rest data-quality, schema/contract evolution, or governance/lineage. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the relevant artifacts: monitoring config, scheduled jobs/DAG files, SQL metric queries, notebooks (.ipynb), training/eval scripts, feature/metric definitions. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS for this lane (from .jje/conventions), treat its blocking rules as additional blocking bars. Load from the repo where present: the reference/baseline convention (frozen train/val vs trailing window, refresh cadence, seasonality handling); the model's label-availability profile (ground-truth latency, feedback mechanism, known label bias e.g. approved-only); the serving/feature platform and where inference inputs and prediction logs are captured (online/offline parity, prediction-log table/topic); the metric/SLO layer defining "model healthy" and its thresholds; the retraining/promotion policy (cadence, triggers, champion-challenger gate, rollback, auto-promote approver); the monitored segments (protected/high-value/high-volume cohorts, fairness/regulatory obligations); the cardinality/schema map of features (continuous/categorical/high-card/embedding); and alerting/on-call conventions (routing, severity, dedup/silence, runbook).

## 3. Run the checks (gate any external tool on `command -v`; missing -> skipped[] + one info finding; never infer)
Mostly reasoning-led. Inspect the diff/SQL/notebook/DAG concretely:
- Coverage triage: grep monitoring code/config for what is computed (`psi|population_stability|ks_2samp|kstest|chi2|wasserstein|jensenshannon|kl_div|entropy|ADWIN|PageHinkley|DDM|EDDM`). Map to the three drift surfaces (input/covariate, prediction/output, concept/performance). Only input-feature drift with no prediction-drift and no performance/label path => concept drift unmonitored.
- Reference-window: find the baseline (`reference|baseline|train_df|expected|ref_window`). Confirm it is frozen and representative — not today-vs-yesterday (hides slow drift), not silently re-baselined each run (drift undetectable by construction). Check seasonality handling.
- Method/type fit: per metric, check the variable type. KS/Wasserstein on continuous only; Chi-square/PSI with a fixed bin/category map on categorical. Flag KS or PSI on high-cardinality IDs or raw embeddings (use domain-classifier or embedding-distance). Verify binning is fixed from the reference (`qcut|cut|bins=`) and empty/new bins get an epsilon, not divide-by-zero/log(0) or a dropped category.
- Threshold provenance: grep `0.1|0.2|0.25|p_value|pvalue|alpha|0.05|threshold`. Require effect size (PSI ~0.1 warn / 0.25 action, KS statistic, Wasserstein) not a bare p-value over large N (p<0.05 on millions of rows fires on trivial shifts; a fixed threshold can fire constantly).
- Multiple-testing: count per-feature tests and whether results aggregate. Many features at alpha=0.05 compound false positives; look for Bonferroni/FDR or a share-of-features-drifted aggregate.
- Sample-size/window guards: each test needs a min-sample guard and a sensible window (`min_samples|window|rolling|n <`). Tiny windows => unstable PSI/KS; unbounded windows hide drift.
- Ground-truth-lag path: if performance is computed, trace label source and join timing. Flag accuracy on the subset that happens to have labels now (survivorship/selection bias), labels joined before they could exist (leakage), or "live accuracy" silently excluding pending-label rows. Where labels are delayed/absent require a proxy (CBPE/DLE, calibration, prediction-drift as leading indicator).
- Prediction/output-drift: confirm score histogram, class balance, calibration are tracked over time — the earliest label-free concept-drift signal; absence is a gap when label lag is high.
- Retraining-trigger safety: read the trigger (`retrain|trigger|promote|deploy_model|schedule`). Confirm it cannot thrash (hysteresis, cooldown, sustained-breach-over-N-windows not a single spike), cannot auto-promote without champion-challenger/holdout validation, and has a rollback.
- Feedback-loop dynamics: determine whether the model's own predictions shape its future training data (recs->clicks, fraud blocks suppressing fraud labels, credit limits gating repayment labels). Flag training data sourced from logged predictions with no exploration/holdout/unbiased collection.
- Segment monitoring: confirm key cohorts are sliced, not just global aggregates (`groupby|segment|cohort|slice`). A flat global metric can mask a collapsing critical segment (Simpson's paradox). Absence on regulated/high-value cohorts is a finding.
- Alert wiring: confirm breaches route to an alert/runbook, not just a dashboard nobody reads; check dedup/silence against alert fatigue and that severity maps to business impact.
- Online/offline parity: confirm monitored inputs are the served values (prediction log/feature store), not recomputed offline (recomputation both hides and fabricates drift).

## 4. Blocking bar
Set blocking:true ONLY with evidence (file:line) for:
- A model with materially delayed/biased labels ships with NO label-free degradation signal (no prediction-drift, no input-drift, no performance estimation) — silent decay for the whole label-lag horizon.
- A health-gating performance metric (live accuracy/AUC) computed on a systematically biased label subset (approved/non-blocked only, or pending-label rows dropped) and reported as overall health — confidently-wrong signal.
- Drift gated on a bare p-value (KS/Chi-square p<0.05) over large production samples with no effect-size floor (fires on meaningless shifts), or a fixed threshold guaranteeing constant firing — unactionable noise that gets silenced.
- A drift test invalid/unstable for the variable type: KS on categorical; PSI/Chi-square with bins recomputed each run or zero-count bins causing divide-by-zero/inf; KS/PSI on raw embeddings or high-cardinality IDs.
- Baseline = short trailing window vs the adjacent window (today vs yesterday) so monotonic drift is mathematically invisible, or baseline silently re-fit every run so drift never accumulates.
- An automated retrain/promotion trigger can auto-deploy without a champion-challenger or holdout gate, and/or has no hysteresis so a single noisy window triggers retrain-and-promote.
- Next-cycle training data sourced from the current model's own logged outputs with no exploration/holdout/unbiased collection — structural degenerate feedback loop (blocking when structural, not incidental).
- A regulated/safety-relevant/explicitly high-value segment monitored only in the global aggregate, where a fairness/SLO obligation on that segment exists.
Everything else advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- Feature-drift-only sold as full coverage while concept drift / P(y|x) change is unmonitored ("we watch the inputs, so we're covered").
- p-value-as-drift-score: treating significance as magnitude on large samples (KS/Chi-square p collapses toward zero as N grows for trivial effects).
- Accuracy theater under label lag: healthy accuracy on whatever rows have labels (biased/survivorship — approved-only, non-blocked-only).
- Re-baselining the reference every run, or today-vs-yesterday windows, so slow drift is structurally invisible.
- PSI/Chi-square with bins recomputed per window or empty bins (divide-by-zero / log(0)) instead of fixed reference bins plus epsilon.
- Wrong-metric-for-type: KS on categoricals, PSI on high-cardinality IDs, raw KS/PSI on embeddings instead of domain-classifier / embedding-distance.
- Alert-fatigue thresholds: noisy single-window triggers with no hysteresis/cooldown that get globally silenced, turning monitoring into decoration.
- Auto-retrain-and-auto-promote with no champion-challenger, no holdout eval, no rollback.
- Degenerate feedback loop: next model trained on the current model's own outputs with no exploration/holdout, amplifying bias and fabricating drift.
- Global-aggregate-only monitoring masking collapse in a critical/regulated/minority segment.
- Monitoring recomputed offline features instead of the served values, so online/offline skew both hides real and invents phantom drift.
- Label leakage in the performance join — joining labels that could not have existed at scoring time — yielding optimistic fictional live metrics.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/model-monitoring-drift-juror.json. ran[]/skipped[] honest. id = drift-<check>-<file>:<line>. Nothing outside the JSON.
