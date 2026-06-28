# Engagement enrichment job

Builds `analytics.fct_engagement_enriched` from one day of raw clickstream
events joined against the marketing and reference dimensions.

## Change in this PR

Previously enrichment only attached country and FX attributes. This PR adds
campaign and device attribution so downstream marketing-mix models can read a
single denormalized fact instead of re-joining `marketing.campaign_dim`
themselves.

- `transforms.py` gains `add_engagement_score` and an expanded output
  projection.
- `reference.py` adds `load_device_dim` and `load_campaign_dim` loaders, each
  projected down to only the columns the join needs.
- `enrich.py` wires the new joins and keeps a partition-leak guard on the input.

## Run

```
spark-submit --py-files jobs.zip \
  jobs/engagement/enrich.py \
  --config conf/engagement_enrichment.yaml \
  --run-date 2026-06-27
```

Join strategies are pinned at the call site in `enrich.py`. The reference
dimensions are documented in `conf/engagement_enrichment.yaml` under
`source_notes`; check that file before changing how any dimension is joined.
