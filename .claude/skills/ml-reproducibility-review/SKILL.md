---
name: ml-reproducibility-review
description: The ML-reproducibility juror's checklist and grep tells for the determinism chain — seeding, GPU/parallel nondeterminism, env pinning, immutable inputs, lineage, notebook drift, and leakage that breaks metric repro.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# ML reproducibility review
You review ONLY whether a training/eval/inference change re-runs to the same (or provably equivalent) model+metrics, and whether the produced artifact traces back to its exact inputs. PRINCIPAL level — block a broken load-bearing link in the determinism chain, not a cosmetic seed in throwaway code. Stay in lane: you do NOT judge statistical validity, data-quality constraints, storage/partition layout, or PII — other jurors own those. Stop at "same inputs => same artifact => traceable artifact".

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect lane artifacts in $CHANGED: training/eval/inference scripts, notebooks (`.ipynb`), pipeline/DAG defs (Airflow/Kubeflow/SageMaker/DVC/Metaflow), experiment-tracking calls (MLflow/W&B), env manifests (lockfiles, Dockerfile, conda), and model-registry/promotion code. Review only those.

## 2. Context to load
If the orchestrator passed PROJECT CONVENTIONS (from .jje/conventions) treat their blocking rules as additional bars. Establish from the repo where present: the reproducibility TIER of the changed code (exploratory/throwaway vs tracked experiment vs production pipeline) — the bar scales with tier; the tracking+registry platform and mandatory lineage fields per run; the data-versioning mechanism and what counts as an immutable snapshot ref; the dependency/lockfile standard and canonical training image; the determinism contract (bit-exact vs tolerance, deterministic kernels mandatory?); accelerator topology (single/multi-GPU DDP/TPU/multi-node); orchestration+notebook policy; the eval/split convention; feature-store pinning.

## 3. Run the checks (gate every external tool on `command -v <tool>`; missing -> skipped[] + one info finding "check skipped: <tool> not installed"; never infer)
Mostly reasoning-led. State the basis for every finding.
- **Seed-completeness sweep.** Enumerate every stochastic lib imported in the diff: `grep -nE 'import random|numpy.*random|torch|tensorflow|jax|lightgbm|xgboost|sklearn'`. Confirm each seeded: `random.seed`, `np.random.seed` OR a passed `np.random.Generator`, `torch.manual_seed`+`torch.cuda.manual_seed_all`, `tf.random.set_seed`, JAX explicit `PRNGKey`. Flag `train_test_split`/`KFold`/`shuffle`/`RandomizedSearchCV`/`resample` missing `random_state=`. Flag `np.random.seed` that has no effect because code consumes a local `Generator`.
- **PyTorch/GPU determinism stanza.** When torch present require `torch.use_deterministic_algorithms(True)`, `cudnn.benchmark=False`, `cudnn.deterministic=True`, and env `CUBLAS_WORKSPACE_CONFIG=:4096:8` (or `:16:8`) set before CUDA init. Red flags: `cudnn.benchmark = True`, missing `use_deterministic_algorithms`. Flag nondeterministic ops (`index_add_`, `scatter_add_`, `bincount`, atomic-add backward) where determinism is required.
- **DataLoader/parallelism seeding.** With `num_workers>0` require seeded `generator=` AND a `worker_init_fn` reseeding NumPy/`random` per worker. Flag `mp.Pool`/`joblib.Parallel`/`tf.data` `.shuffle` without `seed=` where ordering/sampling is load-bearing.
- **PYTHONHASHSEED/hash-ordering.** Grep for reliance on set/dict/`hash()`/`frozenset` ordering feeding splits, sampling, or feature ordering; require `PYTHONHASHSEED` pinned in the run env when such ordering matters.
- **Environment-pinning audit.** Confirm the training path resolves against a committed, fully-resolved, transitively-complete lockfile (`uv.lock`/`poetry.lock`/`requirements.txt` from `pip-compile --generate-hashes`/`conda-lock.yml`/`Pipfile.lock`), not floating `>=`/`~=` deps or `pip install` of floating versions in the Dockerfile/script. If available run `uv lock --check` or `pip-compile --dry-run`. Flag base images pinned by mutable tag (`:latest`) not digest, and missing CUDA/cuDNN/driver capture for GPU runs.
- **Immutable-input check.** Grep training reading `s3://.../latest/`, `current`, runtime `max(date)`, or `SELECT ... FROM table` without snapshot/`VERSION AS OF`/`FOR SYSTEM_TIME`. Require the run to log the resolved data identifier (DVC rev, Delta/Iceberg snapshot id, S3 version-id, content hash). Inspect `dvc.lock`/`.dvc` for changed data deps.
- **Lineage-linkage trace.** Grep `mlflow.log_param(s)|log_artifact|log_input|register_model|set_tag('mlflow.source.git.commit')`, `wandb.config`. Verify a registered/promoted model's run captures {git commit, dataset version, env hash, params, artifact hash} and that metrics link to params/data. Verify uncommitted-diff capture is on or a clean tree is required.
- **Notebook-drift inspection.** For changed `.ipynb`: verify `execution_count` is sequential from 1, no hidden-state cells (use-before-assign in cell order), and the notebook runs headless (papermill/jupytext/nbconvert in CI) if on the training path. Flag a notebook as the canonical producer of a registered model.
- **Leakage-that-breaks-metric-repro.** Confirm split BEFORE any fitted preprocessing. Grep `fit_transform`/`StandardScaler().fit`/`SimpleImputer().fit`/`SMOTE`/feature-selection `.fit(` on the full frame preceding `train_test_split`. For time-series require temporal split (`TimeSeriesSplit`/cutoff), flag random `shuffle=True` on ordered data; confirm split is seeded and recorded.
- **Config externalization.** Confirm hyperparameters+seeds come from a versioned config (Hydra/`params.yaml`/committed argparse defaults) and are logged, not hard-coded magic numbers. Flag `seed = random.randint(...)`/time-seeding without logging the drawn value.
- **Distributed float/reduction determinism.** In DDP/multi-node code check seeds are rank-aware where independence is needed yet global init is fixed, and reductions/all-reduce don't depend on nondeterministic worker-completion order beyond accepted tolerance.

## 4. Blocking bar
Set blocking:true (with evidence at file:line) ONLY for:
- A registered/promoted/shipped (production-tier) model whose producing run does not capture the full reproducibility tuple — immutable dataset version/hash, git commit (clean tree or captured diff), resolved env hash/lockfile, full hyperparameter+seed config, output artifact hash — so it cannot be re-derived or traced. Broken lineage on a promotable artifact is blocking.
- Training/eval reading a MUTABLE data reference (`latest`/`current`/unpinned `max(date)`/table without snapshot-time-travel/S3 path without version-id) so the same code can silently train on different data. Blocking on any tracked or production run.
- A stochastic run on the production path with an incomplete seed chain that materially changes the model or reported metric (torch with no `manual_seed`/`cuda.manual_seed_all`, sklearn split/CV/search without `random_state`, multi-worker DataLoader with no `generator`+`worker_init_fn`). Cosmetic gaps in throwaway code are not blocking.
- GPU training requiring reproducibility that leaves nondeterminism un-suppressed where the contract demands it: `cudnn.benchmark=True`/unset plus missing `use_deterministic_algorithms(True)`/`CUBLAS_WORKSPACE_CONFIG`, or a no-deterministic-kernel op, with no documented tolerance exception.
- Environment not pinned to a resolved, transitively-complete (ideally hash-locked) manifest for a tracked/production run — floating `>=` deps, `pip install` of floating versions in the training image/script, or a base image by mutable tag not digest.
- Preprocessing/feature transforms/resampling FIT on data that includes test/validation rows (fit before split; scaler/imputer/encoder/SMOTE/feature-selection on full X), or a random split on temporally-ordered data where a temporal split is required.
- An out-of-order notebook (non-sequential/duplicate `execution_count`, hidden-state deps) that is the canonical producer of a tracked/registered model or the only definition of the training path, with no headless-executable pipeline/script equivalent.
- A drawn-but-unlogged source of randomness on a tracked run (`seed = randint(...)`/system-time seeding without recording the value) — unrepeatable by construction.
Everything else advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- "Seed theater": top-of-file `random.seed(42)` while NumPy `Generator`s, torch CUDA, DataLoader workers, or sklearn `random_state` go unseeded.
- Splitting AFTER fitting preprocessing (`scaler.fit_transform(X); train_test_split(...)`) — leakage that also breaks metric repro.
- Training on `latest`/`current`/`max(date)` or a non-snapshotted table/feature view — inputs drift under a frozen commit.
- `cudnn.benchmark = True` / auto-tuner left on in a run claiming reproducibility.
- Floating deps (`torch`, `numpy>=`, unpinned `requirements.txt`, `pip install pkg` in Dockerfile, base image `:latest`) — "works on my machine" artifact.
- Notebook-as-pipeline: a registered model whose only producer is an out-of-order notebook that won't re-run top-to-bottom.
- Registered/promoted model with no back-link to producing run, dataset version, or code commit — an orphan artifact.
- Random (`shuffle=True`) or unseeded train/test split on time-ordered data — different rows each run.
- Self-randomizing, unlogged seed (`seed = int(time.time())`/`randint`) on a tracked run.
- `pip freeze` on a dev box called reproducible while CUDA/driver/base-image/`PYTHONHASHSEED` go unrecorded.
- Hard-coded hyperparameters mutated in place between runs with no config versioning or logging.
- Multiprocessing/`joblib`/`tf.data` pipelines whose sampling or ordering is unseeded.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/ml-reproducibility-juror.json. ran[]/skipped[] honest. id = repro-<check>-<file>:<line>. Nothing outside the JSON.
