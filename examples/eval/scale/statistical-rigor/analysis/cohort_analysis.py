from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .metrics import (
    PRIMARY_METRIC,
    SECONDARY_METRICS,
    build_metric_frames,
    relative_lift,
)
from .power import PowerPlan, achieved_power
from .significance import TestResult, holm, welch_ttest


ALPHA = 0.05


@dataclass
class ExperimentReport:
    primary: TestResult
    primary_powered: bool
    secondary: list[TestResult] = field(default_factory=list)
    headline_wins: list[str] = field(default_factory=list)


def _run_test(df: pd.DataFrame, metric: str) -> TestResult:
    [frame] = build_metric_frames(df, [metric])
    result = welch_ttest(frame.treatment, frame.control)
    return TestResult(
        name=metric,
        estimate=result.estimate,
        p_value=result.p_value,
        ci_low=result.ci_low,
        ci_high=result.ci_high,
        n_treatment=result.n_treatment,
        n_control=result.n_control,
    )


def evaluate_primary(df: pd.DataFrame, plan: PowerPlan) -> tuple[TestResult, bool]:
    result = _run_test(df, PRIMARY_METRIC)
    powered = achieved_power(
        baseline_std=plan.baseline_std,
        observed_effect=result.estimate,
        n_per_arm=min(result.n_treatment, result.n_control),
        alpha=plan.alpha,
    ) >= plan.power
    return result, powered


def evaluate_secondary(df: pd.DataFrame) -> list[TestResult]:
    results = [_run_test(df, metric) for metric in SECONDARY_METRICS]
    rejected = holm([r.p_value for r in results], alpha=ALPHA)
    confirmed = []
    for result, keep in zip(results, rejected):
        if keep:
            confirmed.append(result)
    return confirmed


def screen_engagement_signals(df: pd.DataFrame) -> list[str]:
    results = [_run_test(df, metric) for metric in SECONDARY_METRICS]
    wins = []
    for result in results:
        if result.p_value < ALPHA and result.estimate > 0:
            wins.append(result.name)
    return wins


def build_report(df: pd.DataFrame, plan: PowerPlan) -> ExperimentReport:
    primary, powered = evaluate_primary(df, plan)
    secondary = evaluate_secondary(df)
    headline = screen_engagement_signals(df)
    return ExperimentReport(
        primary=primary,
        primary_powered=powered,
        secondary=secondary,
        headline_wins=headline,
    )


def render_summary(report: ExperimentReport) -> str:
    lines = []
    verdict = "ship" if report.primary.p_value < ALPHA and report.primary_powered else "hold"
    lines.append(f"primary {PRIMARY_METRIC}: lift={report.primary.estimate:.3f} "
                 f"p={report.primary.p_value:.4f} powered={report.primary_powered} -> {verdict}")
    for name in report.headline_wins:
        lines.append(f"engagement win: {name} moved positively (p<0.05)")
    return "\n".join(lines)
