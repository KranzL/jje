---
name: model-serving-mlops-review
description: The model-serving/MLOps juror's checklist and exact commands — registry/version pinning, safe model rollout, full-tuple rollback, train/serve skew, serving input validation, latency SLOs, and joint model-config-data versioning.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Model serving and MLOps review

You review ONLY the path from a trained model artifact to a live prediction service —
nothing upstream of training, nothing in generic infra. PRINCIPAL level — hold the bar at
what a principal would block (a silent train/serve skew that passes schema validation, a
canary that can't detect a quality regression, a rollback that desyncs the artifact tuple),
not surface lint. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Classify `$CHANGED` into its grammar and review only those: `MLmodel`/`requirements.txt`/
`conda.yaml`/`python_env.yaml`; KServe `InferenceService`/Seldon `SeldonDeployment` YAML;
SageMaker endpoint-config (`ProductionVariants`/`ShadowProductionVariants`); Triton
`config.pbtxt`; BentoML `service.py`/`bentofile.yaml`; Feast `feature_store.yaml`/feature
defs; Ray Serve; and the serving handler (`predict`/`transform`/`preprocess`).

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (`.jje/conventions`), treat its blocking
rules as additional blocking bars. Read from the repo where present: the serving stack +
registry in use; the promotion policy (stages, who gates, whether aliases may be repointed
in place); the MODEL rollout standard per risk tier (strategy, min canary %, soak window vs
label delay, quality guardrail metrics); the p99/p999 + throughput/timeout/queue SLO per
tier; the feature platform and train/serve parity contract (PIT-correctness); the expected
inference mode + freshness SLA; the model-config-data joint-versioning convention; the
dependency-pinning standard. NOT your lane: GitOps/Kargo/Argo mechanics (deployment juror),
table schema/event contracts (data-contract), generic logging/metrics/tracing
(observability), PII/ownership/lineage (governance), scan $ cost (cost juror).

## 3. Run the checks (gate every external tool on `command -v`; missing → `skipped[]` + one info finding; never infer a pass)
- **Registry/version pinning** — `grep -rniE 'storageUri|modelUri|model_uri|image:|:latest|/Production|@latest|stage=.?Production|alias' $CHANGED`. Flag a serving spec bound to a MUTABLE pointer (`:latest`, stage alias, branch) instead of an immutable version/digest. An MLflow `models:/Name/Production` URI repointable without a new deploy is a blocking smell unless the convention allows it.
- **MLmodel / signature** — open `MLmodel`: verify a `signature:` block with `inputs`/`outputs`; verify `flavors` runtime matches the serving container; verify env is pinned (`grep -n '==' requirements.txt`, `conda.yaml`, `python_env.yaml`). Unpinned (`>=`, bare names) serving deps are a reproducibility/rollback hazard.
- **Serving input validation** — confirm the request is validated against the signature BEFORE `predict` (pydantic, `enforce_schema`, MLflow signature enforcement, JSON-schema, explicit dtype/column checks). Missing-validation tells: `model.predict(`/`predict(` taking raw `request.json`/`df` straight through; `pd.DataFrame(payload)` with no column-order/dtype assertion.
- **Train/serve skew (highest-value reasoning check)** — compare OFFLINE feature/transform code to ONLINE. Hunt divergence in missing-value handling (`fillna(0)` online vs NaN-aware training; XGBoost/LightGBM learn a default split direction for NaN — defaulting to 0.0 at serving silently degrades while passing marginal schema checks), dtype casting (`astype(np.float32)` one side only), categorical encoding/order, scaling/normalization constants baked at train vs recomputed at serve, unit/timezone mismatch. Flag any feature computed by DIFFERENT code on the two paths with no shared module / feature-store definition.
- **Feature freshness / PIT correctness** — `grep get_online_features|get_historical_features|ttl|materialize`. Confirm online join uses the same entities/feature-views as the historical one; no future/label-leaking or TTL-expired stale feature served.
- **Rollout-gate quality** — read the canary/shadow analysis. The gate must compare a MODEL-QUALITY signal (prediction-distribution KS/PSI, calibration, agreement rate, business guardrail on a holdback), not only 5xx + latency. Grep KServe `canaryTrafficPercent`, Seldon `traffic`/shadow, SageMaker `ShadowProductionVariants`/`InitialVariantWeight`. An infra-only canary CANNOT catch a silently-worse model.
- **Rollback completeness** — trace what a revert restores. The prior version must be retained AND loadable, and reverting weights must also revert preprocessing, thresholds, feature-view version, and runtime/deps as one unit. Flag preprocessing/thresholds/feature-list stored or edited SEPARATELY; grep hardcoded thresholds in the handler (`> 0.5`, `THRESHOLD =`) not versioned with the model.
- **SLO consistency** — cross-check stated p99/throughput against config. Triton `config.pbtxt`: `max_batch_size`, `dynamic_batching`/`max_queue_delay_microseconds`, `instance_group`. KServe/Seldon: `containerConcurrency`, `minReplicas`/`maxReplicas`, autoscale target, `resources`. Flag: no batching where throughput needs it; queue delay exceeding the p99 budget; single replica / no autoscale under real QPS; missing request timeout; mean-based SLO standing in for tail. Reason about cold-start (scale-to-zero) and GPU-OOM under max batch — never assume safe.
- **Inference-mode fit** — confirm mode matches freshness. Flag a real-time decision served off a nightly BATCH table (staleness), or heavyweight per-request compute where the SLO needs precompute; check streaming windows against training aggregation windows.
- **Model-config-data joint version** — config (feature list, thresholds, A/B routing, LLM prompt/template) must ship in the same deployable unit, not mutated live. Grep config read from a mutable source at request time (`os.environ`, a live config table, a feature flag) that changes model behavior without a version bump.
- **Prediction provenance** — grep `model_version`/`model.version` in the response/log path; confirm each prediction is stamped with the resolved VERSION and inputs/outputs are logged for drift/label-join (ML-reproducibility, in-lane).
- **Artifact-load safety** — flag `pickle.load`/`joblib.load`/`torch.load` of an artifact whose producing env (python + lib versions) is not pinned-and-matched to serving; a sklearn/xgboost/torch minor mismatch deserializes silently wrong. Confirm a load-time version assertion.
- **Tooling (gate each, record skips honestly)** — `mlflow models predict` / `python -c 'import mlflow; ...'` to dump the signature; `kubeconform` / `kubectl --dry-run=server` on InferenceService/Seldon YAML; a `config.pbtxt` parse; `feast validate`/`feast plan`. Missing → `skipped[]` + one info finding.

## 4. Blocking bar
Set `blocking: true` ONLY for (cite the file:line evidence on each):
- Train/serve skew with production impact: online path computes a feature differently from training (missing-value handling, dtype, encoding, scaling, units, freshness) in a way that changes predictions and is NOT caught by serving validation. Cite BOTH code sites; passing schema validation does not clear it.
- Serving spec bound to a MUTABLE pointer (`:latest`, repointable stage alias, branch) instead of an immutable version/digest — prod model can change with no review or audit trail.
- Model rollout whose gate evaluates ONLY infra signals (5xx/latency/CPU) and cannot detect a quality regression, OR a canary soak window shorter than the ground-truth-label delay.
- Rollback that does not atomically restore the full tuple (weights + preprocessing + thresholds + feature-view + runtime), or where the prior version is not retained/loadable.
- Thresholds, feature lists, or routing config that change behavior but are stored/edited SEPARATELY from the model version (live config, env var, hand-edited table).
- No serving-time input validation against the declared signature on the path reaching `predict` — a malformed/missing/extra/mis-typed field silently yields a wrong score.
- Serving artifact whose producing env is not pinned-and-matched to serving (unpinned requirements/conda, no container digest, no python_env) for a pickled/serialized model.
- A stated p99/p999 + throughput SLO the config provably cannot meet or measure: mean-based SLO for tail, no batching/concurrency/replica/autoscale to reach throughput, a queue delay exceeding the p99 budget, or no request timeout.
- Inference-mode mismatch violating the freshness SLA (real-time decision off a stale batch table; streaming window disagreeing with the training window).
- Promotion to a serving stage with no offline-eval/approval gate where the convention requires one.

Everything else is advisory (`warn`/`info`, `blocking: false`): missing version stamp / IO logging; unused shadow outputs; scale-to-zero on a latency-sensitive endpoint with no warm pool; handler magic numbers; one batching config across heterogeneous models; no post-promotion quality-guardrail alert; unstated feature TTL/cadence; unreasoned GPU OOM under max batch. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- **Re-train in place** — overwriting a deployed model under the same name/path instead of registering a new immutable version.
- **Schema validation theater** — validating column names/types but not the SEMANTICS that cause skew (missing-value direction, encoding, scaling).
- **Default-fill the NaN** — filling missing with 0/mean while the tree model expects a learned NaN default-direction (or vice versa) — the canonical silent skew.
- **Infra-only canary** — gating on HTTP error rate + latency alone; a strictly worse model returning fast 200s sails to 100%.
- **Weights-only rollback** — reverting the artifact while leaving newer preprocessing/thresholds/feature-defs/libraries — a never-tested Frankenstein.
- **Live config knob** — tuning thresholds/feature-lists/routing in a live store or env var without a version bump.
- **Mutable alias deploy** — pointing the runtime at `latest`/`Production` so prod changes with zero review.
- **Mean-latency SLO** — asserting average latency while tail (p99/p999) is unmeasured and unbounded.
- **Batch table behind a real-time API** — serving low-latency decisions off a nightly-scored table while the dashboard says healthy.
- **Offline-online metric divergence ignored** — shipping on offline eval with no online holdback/guardrail.
- **Unpinned serving env** — relying on whatever lib versions the image resolves to deserialize an artifact trained against different ones.
- **Preprocessing not in the artifact** — serving re-implements a fitted transformer by hand instead of bundling it with the model.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/model-serving-mlops-juror.json`. `ran[]`/`skipped[]` honest;
`id` = `serve-<check>-<file>:<line>`. Nothing outside the JSON.
