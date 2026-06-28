from dataclasses import dataclass, field
from typing import List


TREATMENT = "received_onboarding_call"

OUTCOME_BINARY = "retained_90d"
OUTCOME_CONTINUOUS = "revenue_90d"


BASELINE_CATEGORICAL = [
    "acquisition_channel",
    "device_type",
    "geo_region",
    "plan_tier_at_signup",
]

BASELINE_NUMERIC = [
    "prior_trial_count",
    "signup_dow",
    "signup_hour",
]

BASELINE_BINARY = [
    "marketing_consent",
    "is_returning_user",
    "high_intent_channel",
    "activated_within_7d",
]


@dataclass
class AdjustmentSet:
    categorical: List[str] = field(default_factory=lambda: list(BASELINE_CATEGORICAL))
    numeric: List[str] = field(default_factory=lambda: list(BASELINE_NUMERIC))
    binary: List[str] = field(default_factory=lambda: list(BASELINE_BINARY))

    def all_columns(self) -> List[str]:
        return self.categorical + self.numeric + self.binary

    def design_columns(self) -> List[str]:
        return [c for c in self.all_columns() if c != TREATMENT]


def default_adjustment_set() -> AdjustmentSet:
    return AdjustmentSet()


MEDIATOR = "activated_within_7d"
