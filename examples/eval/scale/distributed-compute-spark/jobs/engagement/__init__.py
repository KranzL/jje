"""Engagement enrichment Spark jobs.

This package builds the daily ``fct_engagement_enriched`` table from raw
clickstream events joined against marketing and reference dimensions. It runs
on the shared analytics cluster (Spark 3.5, AQE enabled by default).
"""

__all__ = ["enrich", "reference", "transforms", "config"]
