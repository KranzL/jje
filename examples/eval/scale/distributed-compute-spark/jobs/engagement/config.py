"""Configuration loading for the engagement enrichment job."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclasses.dataclass(frozen=True)
class SourceTables:
    events: str
    campaign_dim: str
    country_lookup: str
    currency_rates: str
    device_dim: str


@dataclasses.dataclass(frozen=True)
class JobConfig:
    run_date: str
    output_table: str
    output_partitions: int
    shuffle_partitions: int
    sources: SourceTables

    @property
    def event_partition_filter(self) -> str:
        return f"event_date = '{self.run_date}'"


def _coerce_sources(raw: Dict[str, Any]) -> SourceTables:
    return SourceTables(
        events=raw["events"],
        campaign_dim=raw["campaign_dim"],
        country_lookup=raw["country_lookup"],
        currency_rates=raw["currency_rates"],
        device_dim=raw["device_dim"],
    )


def load_config(path: str | Path, run_date: str) -> JobConfig:
    data = yaml.safe_load(Path(path).read_text())
    job = data["job"]
    return JobConfig(
        run_date=run_date,
        output_table=job["output_table"],
        output_partitions=int(job.get("output_partitions", 200)),
        shuffle_partitions=int(job.get("shuffle_partitions", 400)),
        sources=_coerce_sources(data["sources"]),
    )
