import numpy as np
import pandas as pd
from scipy import stats


VARIANTS = ("control", "treatment")


def assign_bucket(user_id: str, salt: str = "engagement_v2") -> str:
    h = abs(hash(f"{salt}:{user_id}")) % 1000
    return "treatment" if h >= 500 else "control"


def load_sessions(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[df["session_start"].notna()].copy()
    df["bucket"] = df["user_id"].map(assign_bucket)
    df = df[df["bucket"].isin(VARIANTS)]
    return df


def _winsorize(s: pd.Series, upper_q: float = 0.99) -> pd.Series:
    cap = s.quantile(upper_q)
    return s.clip(upper=cap)


def collapse_to_user(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["active_minutes"] = _winsorize(work["active_minutes"].fillna(0.0))
    per_user = (
        work.groupby(["user_id", "bucket"], as_index=False)
        .agg(
            sessions=("session_start", "size"),
            active_minutes=("active_minutes", "sum"),
            any_purchase=("completed_checkout", "max"),
        )
    )
    return per_user


def check_sample_ratio(per_user: pd.DataFrame) -> dict:
    counts = per_user["bucket"].value_counts().reindex(VARIANTS).fillna(0)
    n = counts.sum()
    chi2, p = stats.chisquare(counts.values, np.array([n / 2, n / 2]))
    return {
        "control_users": int(counts["control"]),
        "treatment_users": int(counts["treatment"]),
        "srm_p_value": float(p),
        "srm_flag": bool(p < 0.001),
    }


def readout(per_user: pd.DataFrame, metric: str = "active_minutes") -> dict:
    rows = {}
    for variant in VARIANTS:
        cell = per_user.loc[per_user["bucket"] == variant, metric]
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
    per_user = collapse_to_user(df)
    result = readout(per_user)
    result["srm"] = check_sample_ratio(per_user)
    return result


if __name__ == "__main__":
    import sys

    out = run(sys.argv[1])
    print(f"rel lift: {out['relative_lift']:.4f}  p={out['p_value']:.4f}")
    print(f"95% CI on abs lift: {out['ci_95']}")
