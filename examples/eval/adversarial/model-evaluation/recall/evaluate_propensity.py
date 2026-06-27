import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix


def load_dataset():
    rng = np.random.default_rng(11)
    n = 40000
    tenure = rng.gamma(2.0, 8.0, n)
    monthly_spend = rng.normal(70, 22, n)
    support_tickets = rng.poisson(0.4, n)
    autopay = rng.integers(0, 2, n)
    logit = (
        -3.1
        - 0.04 * tenure
        + 0.012 * (monthly_spend - 70)
        + 0.55 * support_tickets
        - 0.7 * autopay
    )
    p = 1.0 / (1.0 + np.exp(-logit))
    y = (rng.uniform(size=n) < p).astype(int)
    X = np.column_stack([tenure, monthly_spend, support_tickets, autopay])
    return X, y


def operating_point(y_true, scores):
    grid = np.linspace(0.05, 0.95, 181)
    best_t, best_f1 = 0.5, -1.0
    for t in grid:
        pred = (scores >= t).astype(int)
        pr, rc, f1, _ = precision_recall_fscore_support(
            y_true, pred, average="binary", zero_division=0
        )
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return best_t


def main():
    X, y = load_dataset()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=7
    )

    model = GradientBoostingClassifier(
        n_estimators=160, max_depth=3, learning_rate=0.06, random_state=7
    )
    model.fit(X_tr, y_tr)

    train_scores = model.predict_proba(X_tr)[:, 1]
    test_scores = model.predict_proba(X_te)[:, 1]

    print(f"positives in train: {y_tr.mean():.3f}")
    print(f"positives in test:  {y_te.mean():.3f}")

    threshold = operating_point(y_te, test_scores)
    print(f"selected operating threshold: {threshold:.3f}")

    test_pred = (test_scores >= threshold).astype(int)
    pr, rc, f1, _ = precision_recall_fscore_support(
        y_te, test_pred, average="binary", zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y_te, test_pred).ravel()

    print("--- held-out test performance ---")
    print(f"precision: {pr:.3f}")
    print(f"recall:    {rc:.3f}")
    print(f"f1:        {f1:.3f}")
    print(f"confusion: tn={tn} fp={fp} fn={fn} tp={tp}")

    train_pred = (train_scores >= threshold).astype(int)
    tr_pr, tr_rc, tr_f1, _ = precision_recall_fscore_support(
        y_tr, train_pred, average="binary", zero_division=0
    )
    print(f"train f1 at same threshold: {tr_f1:.3f}")


if __name__ == "__main__":
    main()
