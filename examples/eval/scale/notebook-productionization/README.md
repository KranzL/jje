# Weekly churn scoring job

Productionizes the exploratory `churn_scoring` notebook into a scheduled papermill job.

## Layout

- `notebooks/build_churn_features.ipynb` — materializes the feature frame (run first).
- `notebooks/churn_scoring.ipynb` — scores accounts and exports the high-risk cohort.
- `jobs/run_churn_scoring.py` — papermill entrypoint invoked by the scheduler.
- `config/churn_scoring.yaml` — job parameters and runtime limits.

## Running locally

The job reads its parameters from the config and injects them into the parameters
cell. Output location is derived at runtime and can be overridden with the
`CHURN_EXPORT_ROOT` environment variable.

```bash
python jobs/run_churn_scoring.py --scoring-date 2026-06-22
```

To iterate on the notebook interactively before committing, you can point papermill
at a scratch copy under your home directory, e.g.:

```bash
papermill notebooks/churn_scoring.ipynb ~/scratch/churn_dryrun.ipynb \
  -p scoring_date 2026-06-22 -p output_path /tmp/scores.parquet
```

The executed notebook for each scheduled run is archived under
`$CHURN_RUN_LOG_DIR` (default `/tmp/churn_runs`).

## Reproducibility

Both notebooks are expected to execute cold, top-to-bottom, with no reliance on
prior kernel state. CI runs `nbconvert --execute` on a clean kernel as a gate.
