import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


SECONDARY_METRICS = [
    "sessions_per_week",
    "docs_created",
    "shares_sent",
    "comments_added",
    "search_queries",
    "integrations_connected",
]


def load_panel(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["arm"] = df["bucket"].map({"holdout": 0, "treatment": 1})
    return df.dropna(subset=["arm"])


def _two_sample(frame: pd.DataFrame, metric: str) -> dict:
    a = frame.loc[frame["arm"] == 0, metric].dropna()
    b = frame.loc[frame["arm"] == 1, metric].dropna()
    t, p = stats.ttest_ind(b, a, equal_var=False)
    return {
        "metric": metric,
        "delta": float(b.mean() - a.mean()),
        "p_raw": float(p),
    }


def scan_secondary(path: str, alpha: float = 0.05) -> pd.DataFrame:
    df = load_panel(path)
    records = [_two_sample(df, m) for m in SECONDARY_METRICS]
    out = pd.DataFrame(records)

    reject, p_adj, _, _ = multipletests(out["p_raw"].values, alpha=alpha, method="fdr_bh")
    out["p_adj"] = p_adj
    out["significant"] = reject
    return out.sort_values("p_adj").reset_index(drop=True)


def summarize(scan: pd.DataFrame) -> str:
    hits = scan[scan["significant"]]
    if hits.empty:
        return "No secondary metric moved after false-discovery control."
    lines = [
        f"{r.metric}: delta={r.delta:+.2f} (q={r.p_adj:.3f})"
        for r in hits.itertuples()
    ]
    return "Secondary movers (FDR-controlled):\n" + "\n".join(lines)


if __name__ == "__main__":
    scan = scan_secondary("s3://exp/engagement/2026_q2.parquet")
    print(scan.to_string(index=False))
    print(summarize(scan))
