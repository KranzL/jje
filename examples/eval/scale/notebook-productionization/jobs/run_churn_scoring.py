import argparse
import datetime as dt
import os
import pathlib

import papermill as pm
import yaml

CONFIG_DEFAULT = pathlib.Path(__file__).resolve().parents[1] / "config" / "churn_scoring.yaml"
NOTEBOOK = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "churn_scoring.ipynb"


def load_config(path):
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def resolve_scoring_date(raw):
    if raw:
        return dt.date.fromisoformat(raw).isoformat()
    return dt.date.today().isoformat()


def build_output_path(base_dir, scoring_date, fmt):
    base = pathlib.Path(os.environ.get("CHURN_EXPORT_ROOT", base_dir))
    target = base / f"scoring_date={scoring_date}"
    target.mkdir(parents=True, exist_ok=True)
    return str(target / f"scores.{fmt}")


def main():
    parser = argparse.ArgumentParser(description="Run the weekly churn scoring notebook as a job.")
    parser.add_argument("--config", default=str(CONFIG_DEFAULT))
    parser.add_argument("--scoring-date", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    params = dict(config["parameters"])

    scoring_date = resolve_scoring_date(args.scoring_date or params.get("scoring_date"))
    params["scoring_date"] = scoring_date
    params["output_path"] = build_output_path(
        params["output_dir"], scoring_date, params["output_format"]
    )

    executed_dir = pathlib.Path(os.environ.get("CHURN_RUN_LOG_DIR", "/tmp/churn_runs"))
    executed_dir.mkdir(parents=True, exist_ok=True)
    executed_nb = executed_dir / f"churn_scoring_{scoring_date}.ipynb"

    runtime = config["runtime"]
    pm.execute_notebook(
        input_path=str(NOTEBOOK),
        output_path=str(executed_nb),
        parameters=params,
        kernel_name=runtime["kernel"],
        log_output=runtime["log_output"],
        execution_timeout=runtime["papermill_timeout_seconds"],
    )
    print(f"churn scoring complete: {params['output_path']}")


if __name__ == "__main__":
    main()
