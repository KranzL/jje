import numpy as np
from scipy import stats

ALPHA = 0.05

METRICS = [
    "checkout_conversion",
    "add_to_cart_rate",
    "session_duration",
    "search_ctr",
    "revenue_per_user",
    "pages_per_session",
    "signup_rate",
    "wishlist_adds",
    "support_contacts",
    "app_open_rate",
]


def load_experiment():
    rng = np.random.default_rng(7)
    control = {m: rng.normal(0.0, 1.0, size=4000) for m in METRICS}
    treatment = {m: rng.normal(0.0, 1.0, size=4000) for m in METRICS}
    return control, treatment


def main():
    control, treatment = load_experiment()

    winners = []
    for metric in METRICS:
        c = control[metric]
        t = treatment[metric]
        _, p = stats.ttest_ind(c, t, equal_var=False)
        lift = t.mean() - c.mean()
        if p < ALPHA:
            winners.append((metric, lift, p))
            print(f"{metric}: SIGNIFICANT lift={lift:+.4f} p={p:.4f}")
        else:
            print(f"{metric}: flat lift={lift:+.4f} p={p:.4f}")

    if winners:
        best = min(winners, key=lambda r: r[2])
        print(f"\nShip decision: launch on {best[0]} (p={best[2]:.4f} < {ALPHA})")
    else:
        print("\nShip decision: hold")


if __name__ == "__main__":
    main()
