import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression


ADJUSTMENT = [
    "log_arr",
    "seats",
    "tenure_days",
    "industry_tech",
    "industry_finance",
    "prior_term_renewed",
    "support_sev1_prior_year",
    "adoption_index",
]


def _industry_dummies(frame: pd.DataFrame) -> pd.DataFrame:
    frame["industry_tech"] = (frame["industry"] == "tech").astype(int)
    frame["industry_finance"] = (frame["industry"] == "finance").astype(int)
    return frame


def _adoption_window(events: pd.DataFrame, accounts: pd.DataFrame) -> pd.Series:
    joined = events.merge(
        accounts[["account_id", "touch_date"]], on="account_id", how="inner"
    )
    joined["age_days"] = (joined["event_ts"] - joined["touch_date"]).dt.days
    window = joined[(joined["age_days"] >= 0) & (joined["age_days"] < 60)]
    breadth = window.groupby("account_id")["feature_key"].nunique()
    return breadth.rename("adoption_index")


def build_frame(accounts_path: str, events_path: str) -> pd.DataFrame:
    accounts = pd.read_parquet(accounts_path)
    events = pd.read_parquet(events_path)
    accounts["touch_date"] = pd.to_datetime(accounts["touch_date"])
    events["event_ts"] = pd.to_datetime(events["event_ts"])

    accounts["log_arr"] = np.log1p(accounts["arr_usd"])
    accounts["treated"] = (accounts["outreach_arm"] == "proactive").astype(int)
    accounts = _industry_dummies(accounts)

    adoption = _adoption_window(events, accounts)
    accounts = accounts.merge(adoption, on="account_id", how="left")
    accounts["adoption_index"] = accounts["adoption_index"].fillna(0)

    keep = ["account_id", "treated", "renewed"] + ADJUSTMENT
    return accounts.dropna(subset=keep)[keep]


def propensity_weights(frame: pd.DataFrame) -> np.ndarray:
    X = frame[ADJUSTMENT].to_numpy()
    t = frame["treated"].to_numpy()
    model = LogisticRegression(max_iter=2000, C=1.0)
    model.fit(X, t)
    ps = model.predict_proba(X)[:, 1]
    ps = np.clip(ps, 0.02, 0.98)
    return t / ps + (1 - t) / (1 - ps)


def estimate(frame: pd.DataFrame) -> dict:
    w = propensity_weights(frame)
    design = sm.add_constant(frame[["treated"] + ADJUSTMENT])
    glm = sm.GLM(
        frame["renewed"],
        design,
        family=sm.families.Binomial(),
        freq_weights=w,
    ).fit()
    coef = glm.params["treated"]
    lo, hi = glm.conf_int().loc["treated"]
    return {
        "ate_logodds": float(coef),
        "odds_ratio": float(np.exp(coef)),
        "ci_low": float(np.exp(lo)),
        "ci_high": float(np.exp(hi)),
        "n": int(frame.shape[0]),
    }


def main() -> None:
    frame = build_frame(
        "s3://cs/accounts/2026_renewals.parquet",
        "s3://cs/product/feature_events.parquet",
    )
    result = estimate(frame)
    direction = "lifts" if result["odds_ratio"] > 1 else "lowers"
    print(
        f"Proactive outreach {direction} renewal odds "
        f"(OR={result['odds_ratio']:.2f}, "
        f"95% CI [{result['ci_low']:.2f}, {result['ci_high']:.2f}], "
        f"n={result['n']})."
    )


if __name__ == "__main__":
    main()
