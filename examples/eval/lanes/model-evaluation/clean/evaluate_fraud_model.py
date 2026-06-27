import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score, average_precision_score


def load_data():
    X, y = make_classification(
        n_samples=20000,
        n_features=30,
        weights=[0.98, 0.02],
        random_state=7,
    )
    return X, y


def main():
    X, y = load_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=7, stratify=y
    )

    base_rate = y_test.mean()

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(X_train, y_train)

    baseline = DummyClassifier(strategy="prior")
    baseline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    base_proba = baseline.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, proba)
    pr_auc = average_precision_score(y_test, proba)
    base_pr_auc = average_precision_score(y_test, base_proba)

    print(f"positive base rate: {base_rate:.4f}")
    print(f"holdout ROC-AUC: {auc:.4f}")
    print(f"holdout PR-AUC: {pr_auc:.4f} (prior baseline {base_pr_auc:.4f})")
    return auc, pr_auc


if __name__ == "__main__":
    main()
