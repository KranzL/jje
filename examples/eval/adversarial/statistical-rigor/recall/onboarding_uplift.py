import numpy as np
import pandas as pd
from scipy import stats


REGIONS = ["us_west", "us_east", "emea", "latam", "apac", "anz", "nordics"]


def load_activation_panel(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[df["enrolled_at"].notna()].copy()
    df["activated"] = df["first_value_event_at"].notna().astype(int)
    df["arm"] = df["variant"].map({"control": 0, "guided": 1})
    return df.dropna(subset=["arm", "region"])


def winsorize(series: pd.Series, limit: float = 0.01) -> pd.Series:
    lo, hi = series.quantile(limit), series.quantile(1 - limit)
    return series.clip(lo, hi)


def region_effect(frame: pd.DataFrame) -> dict:
    control = frame.loc[frame["arm"] == 0, "time_to_value_hours"]
    guided = frame.loc[frame["arm"] == 1, "time_to_value_hours"]
    control = winsorize(control)
    guided = winsorize(guided)
    t, p = stats.ttest_ind(guided, control, equal_var=False)
    lift = guided.mean() - control.mean()
    return {
        "n_control": int(control.shape[0]),
        "n_guided": int(guided.shape[0]),
        "mean_lift_hours": float(lift),
        "t_stat": float(t),
        "p_value": float(p),
    }


def evaluate(path: str) -> pd.DataFrame:
    df = load_activation_panel(path)
    rows = []
    for region in REGIONS:
        sub = df[df["region"] == region]
        if sub["arm"].nunique() < 2:
            continue
        result = region_effect(sub)
        result["region"] = region
        rows.append(result)

    report = pd.DataFrame(rows).set_index("region")
    report = report.sort_values("p_value")
    return report


def headline(report: pd.DataFrame) -> str:
    significant = report[report["p_value"] < 0.05]
    if significant.empty:
        return "No regional effect detected for guided onboarding."
    top = significant.iloc[0]
    return (
        f"Guided onboarding reduces time-to-value in {significant.index[0]} "
        f"by {abs(top['mean_lift_hours']):.1f}h (p={top['p_value']:.3f}); "
        f"recommend rollout prioritized to this region."
    )


if __name__ == "__main__":
    rep = evaluate("s3://growth/activation/2026_q2.parquet")
    print(rep.to_string())
    print(headline(rep))
