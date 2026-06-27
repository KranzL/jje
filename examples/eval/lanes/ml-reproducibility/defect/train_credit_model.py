import hashlib
import os
import random
import subprocess

import numpy as np
import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

CONFIG = {
    "seed": 1337,
    "dataset_snapshot": "s3://datasets/credit/latest/",
    "n_estimators": 400,
    "max_depth": 12,
    "test_size": 0.2,
    "registered_model_name": "credit_default_rf",
}

FEATURES = ["utilization", "income", "age", "num_late_payments"]
LABEL = "defaulted"


def set_seeds(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()


def env_lockfile_hash(path: str = "requirements.lock") -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def load_dataset(snapshot_uri: str) -> pd.DataFrame:
    return pd.read_parquet(snapshot_uri)


def main() -> None:
    set_seeds(CONFIG["seed"])

    frame = load_dataset(CONFIG["dataset_snapshot"])
    X = frame[FEATURES]
    y = frame[LABEL]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=CONFIG["test_size"],
        random_state=CONFIG["seed"],
        stratify=y,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=CONFIG["n_estimators"],
        max_depth=CONFIG["max_depth"],
        random_state=CONFIG["seed"],
        n_jobs=1,
    )
    model.fit(X_train_scaled, y_train)

    auc = roc_auc_score(y_test, model.predict_proba(X_test_scaled)[:, 1])

    with mlflow.start_run() as run:
        mlflow.log_params(CONFIG)
        mlflow.set_tag("mlflow.source.git.commit", git_commit())
        mlflow.log_param("dataset_version", CONFIG["dataset_snapshot"])
        mlflow.log_param("env_lockfile_sha256", env_lockfile_hash())
        mlflow.log_metric("roc_auc", auc)
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=CONFIG["registered_model_name"],
        )
        print(f"run_id={run.info.run_id} auc={auc:.4f}")


if __name__ == "__main__":
    main()
