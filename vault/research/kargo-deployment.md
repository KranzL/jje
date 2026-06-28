---
type: research
tags: [research, deploy, gitops]
verified: 2026-06
---
# Research: Kargo + deployment

Basis for the [[deployment]] juror ([[deploy]] lane). Verified against the
official Kargo docs (docs.kargo.io).

## Model
Warehouse (`imageSelectionStrategy`: SemVer/Lexical/Digest/NewestBuild;
`freightCreationPolicy`: **Automatic**/Manual) → **Freight** (a fixed artifact
snapshot) → Stage (`requestedFreight` from a Warehouse or upstream Stages) →
Promotion (steps: git-clone, kustomize-set-image, git-push, git-open-pr,
git-wait-for-pr, argocd-update, argocd-wait) → Verification (AnalysisTemplates =
Argo Rollouts CRDs; only a Successful AnalysisRun marks Freight verified).

## Blocks on
prod Stage with no verification gate, ungated promotion (no `argocd-update`),
stage-skipping (direct Warehouse source on prod / availabilityStrategy != All),
unpinned Freight, no human gate to prod, canary with no rollback/soak, plaintext
secrets.

> [!note] "manual git edits bypass the Warehouse" is a reviewer *inference* (Kargo
> relies on Git-as-source-of-truth + branch protection) → kept advisory.
