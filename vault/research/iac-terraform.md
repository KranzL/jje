---
type: research
tags: [research, iac]
verified: 2026-06
---
# Research: AWS + Terraform review

Basis for the [[terraform]] juror ([[iac]] lane).

## Tooling (with corrections)
- **Use Trivy** (`trivy config`) — `tfsec` is **deprecated** (merged into Trivy).
- **Use Checkov** (deepest, graph-aware) — **Terrascan is archived** (2025-11-20).
- Plus `tflint` (+aws), `infracost diff`, `conftest`/OPA, `terraform validate/plan`.

## Blocks on
public S3, `0.0.0.0/0` ingress on sensitive ports, unencrypted at rest, IAM
`*:*`, public RDS, plaintext secrets, committed tfstate / no remote-locked
backend, unpinned providers.

> [!note] The [[scale-eval]] caught [[terraform]] missing a buried IAM defect
> **because checkov/trivy were absent** — the clearest case for [[tool-backing]].
> Fix: hard-require the scanners.
