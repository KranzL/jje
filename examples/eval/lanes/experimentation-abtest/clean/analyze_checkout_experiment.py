import numpy as np
from scipy import stats

RANDOMIZATION_UNIT = "user_id"
ALPHA = 0.05
EXPECTED_SPLIT = 0.5

USER_QUERY = """
SELECT
    a.user_id,
    a.variant,
    CASE WHEN COUNT(o.order_id) > 0 THEN 1 ELSE 0 END AS converted
FROM assignment a
JOIN sessions s ON s.user_id = a.user_id
LEFT JOIN orders o ON o.session_id = s.session_id
WHERE s.session_start BETWEEN '2026-06-01' AND '2026-06-14'
GROUP BY a.user_id, a.variant
"""


def load_users():
    rng = np.random.default_rng(11)
    rows = []
    for user_id in range(8000):
        variant = "treatment" if rng.random() < EXPECTED_SPLIT else "control"
        p = 0.121 if variant == "treatment" else 0.118
        n_sessions = 1 + rng.poisson(3)
        converted = int(any(rng.random() < p for _ in range(n_sessions)))
        rows.append((user_id, variant, converted))
    return rows


def srm_check(rows):
    n_t = sum(1 for _, v, _ in rows if v == "treatment")
    n_c = sum(1 for _, v, _ in rows if v == "control")
    total = n_t + n_c
    expected = total * EXPECTED_SPLIT
    chisq = (n_t - expected) ** 2 / expected + (n_c - expected) ** 2 / expected
    p = stats.chi2.sf(chisq, df=1)
    return p


def main():
    rows = load_users()

    srm_p = srm_check(rows)
    if srm_p < 0.001:
        raise SystemExit(f"SRM detected (p={srm_p:.5f}), aborting readout")

    t_users = np.array([c for _, v, c in rows if v == "treatment"])
    c_users = np.array([c for _, v, c in rows if v == "control"])

    stat, p_value = stats.ttest_ind(t_users, c_users, equal_var=False)
    lift = t_users.mean() - c_users.mean()

    print(f"SRM p-value: {srm_p:.5f}")
    print(f"treatment conversion: {t_users.mean():.4f} (n={t_users.size} users)")
    print(f"control conversion:   {c_users.mean():.4f} (n={c_users.size} users)")
    print(f"absolute lift: {lift:.4f}, p-value: {p_value:.4f}")

    if p_value < ALPHA and lift > 0:
        print("DECISION: ship treatment")
    else:
        print("DECISION: do not ship")


if __name__ == "__main__":
    main()
