import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score


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

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=7
    )

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)

    print(f"holdout ROC-AUC: {auc:.4f}")
    return auc


if __name__ == "__main__":
    main()
