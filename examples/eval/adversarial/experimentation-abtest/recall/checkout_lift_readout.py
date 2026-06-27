import numpy as np
import pandas as pd
from scipy import stats


VARIANTS = ("control", "treatment")


def assign_bucket(user_id: str, salt: str = "checkout_v3") -> str:
    h = abs(hash(f"{salt}:{user_id}")) % 1000
    return "treatment" if h >= 500 else "control"


def load_sessions(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[df["session_start"].notna()].copy()
    df["bucket"] = df["user_id"].map(assign_bucket)
    df = df[df["bucket"].isin(VARIANTS)]
    return df


def check_sample_ratio(df: pd.DataFrame) -> dict:
    users = df.drop_duplicates("user_id")
    counts = users["bucket"].value_counts().reindex(VARIANTS).fillna(0)
    n = counts.sum()
    expected = np.array([n / 2, n / 2])
    chi2, p = stats.chisquare(counts.values, expected)
    return {
        "control_users": int(counts["control"]),
        "treatment_users": int(counts["treatment"]),
        "srm_p_value": float(p),
        "srm_flag": bool(p < 0.001),
    }


def _winsorize(s: pd.Series, upper_q: float = 0.99) -> pd.Series:
    cap = s.quantile(upper_q)
    return s.clip(upper=cap)


def readout(df: pd.DataFrame, metric: str = "completed_checkout") -> dict:
    work = df.copy()
    work["completed_checkout"] = work["completed_checkout"].astype(float)
    work["revenue"] = _winsorize(work["revenue"].fillna(0.0))

    rows = {}
    for variant in VARIANTS:
        cell = work.loc[work["bucket"] == variant, metric]
        rows[variant] = {
            "n": int(cell.shape[0]),
            "mean": float(cell.mean()),
            "var": float(cell.var(ddof=1)),
        }

    c, t = rows["control"], rows["treatment"]
    abs_lift = t["mean"] - c["mean"]
    rel_lift = abs_lift / c["mean"] if c["mean"] else np.nan

    se = np.sqrt(c["var"] / c["n"] + t["var"] / t["n"])
    z = abs_lift / se if se else np.nan
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    half_width = stats.norm.ppf(0.975) * se

    return {
        "metric": metric,
        "control": c,
        "treatment": t,
        "absolute_lift": abs_lift,
        "relative_lift": rel_lift,
        "ci_95": (abs_lift - half_width, abs_lift + half_width),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
    }


def run(path: str) -> dict:
    df = load_sessions(path)
    srm = check_sample_ratio(df)
    result = readout(df)
    result["srm"] = srm
    return result


if __name__ == "__main__":
    import sys

    out = run(sys.argv[1])
    print(f"rel lift: {out['relative_lift']:.4f}  p={out['p_value']:.4f}")
    print(f"95% CI on abs lift: {out['ci_95']}")
