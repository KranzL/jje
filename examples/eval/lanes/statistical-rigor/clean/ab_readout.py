import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

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

    metrics = []
    pvals = []
    lifts = []
    for metric in METRICS:
        c = control[metric]
        t = treatment[metric]
        _, p = stats.ttest_ind(c, t, equal_var=False)
        metrics.append(metric)
        pvals.append(p)
        lifts.append(t.mean() - c.mean())

    reject, p_adj, _, _ = multipletests(pvals, alpha=ALPHA, method="holm")

    winners = []
    for metric, lift, p, p_corr, sig in zip(metrics, lifts, pvals, p_adj, reject):
        status = "SIGNIFICANT" if sig else "flat"
        print(f"{metric}: {status} lift={lift:+.4f} p={p:.4f} p_holm={p_corr:.4f}")
        if sig:
            winners.append((metric, lift, p_corr))

    if winners:
        best = min(winners, key=lambda r: r[2])
        print(f"\nShip decision: launch on {best[0]} (Holm p={best[2]:.4f} < {ALPHA})")
    else:
        print(f"\nShip decision: hold (no metric survives Holm at alpha={ALPHA})")


if __name__ == "__main__":
    main()
