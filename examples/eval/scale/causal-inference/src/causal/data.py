import pandas as pd
import numpy as np


SIGNUP_FIELDS = [
    "user_id",
    "signup_ts",
    "acquisition_channel",
    "device_type",
    "geo_region",
    "plan_tier_at_signup",
    "prior_trial_count",
    "marketing_consent",
]

OUTCOME_FIELDS = [
    "user_id",
    "retained_90d",
    "revenue_90d",
]


def load_cohort(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["signup_ts"] = pd.to_datetime(df["signup_ts"], utc=True)
    df["onboarding_call_ts"] = pd.to_datetime(df["onboarding_call_ts"], utc=True)
    df["first_activation_ts"] = pd.to_datetime(df["first_activation_ts"], utc=True)
    return df


def derive_treatment(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["received_onboarding_call"] = (
        out["onboarding_call_ts"].notna()
        & (out["onboarding_call_ts"] <= out["signup_ts"] + pd.Timedelta(days=1))
    ).astype(int)
    return out


def derive_pretreatment_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["signup_dow"] = out["signup_ts"].dt.dayofweek
    out["signup_hour"] = out["signup_ts"].dt.hour
    out["is_returning_user"] = (out["prior_trial_count"] > 0).astype(int)
    out["high_intent_channel"] = out["acquisition_channel"].isin(
        ["paid_search", "referral"]
    ).astype(int)
    return out


def derive_activation_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    days_to_activation = (out["first_activation_ts"] - out["signup_ts"]).dt.days
    out["activated_within_7d"] = (
        out["first_activation_ts"].notna() & (days_to_activation <= 7)
    ).astype(int)
    out["days_to_first_activation"] = days_to_activation
    return out


def build_analysis_frame(path: str) -> pd.DataFrame:
    df = load_cohort(path)
    df = derive_treatment(df)
    df = derive_pretreatment_features(df)
    df = derive_activation_features(df)
    keep = (
        SIGNUP_FIELDS
        + ["received_onboarding_call", "signup_dow", "signup_hour",
           "is_returning_user", "high_intent_channel",
           "activated_within_7d", "days_to_first_activation"]
        + ["retained_90d", "revenue_90d"]
    )
    return df[[c for c in keep if c in df.columns]].dropna(subset=["retained_90d"])
