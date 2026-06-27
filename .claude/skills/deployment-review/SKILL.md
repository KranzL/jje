---
name: deployment-review
description: The deployment juror's checklist and exact commands for GitOps progressive-delivery and promotion safety across Kargo and Argo CD / Argo Rollouts.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Deployment review

You review ONLY GitOps progressive-delivery / promotion safety — Kargo (Warehouse,
Freight, Stage, Promotion, verification) and Argo CD / Argo Rollouts gates. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD -- '*.yaml' '*.yml')"
```
Detect Kargo/Argo manifests: `kind:` of `Warehouse|Stage|Promotion|PromotionTemplate|Project`,
Argo CD `Application`, or `AnalysisTemplate`. Reason over each as YAML.

## 2. Run the checks (gate each external tool on `command -v`; missing -> `skipped[]` + one info finding; never infer)
VERIFIED Kargo model — cite the field when flagging: a Warehouse has `imageSelectionStrategy`
(`SemVer|Lexical|Digest|NewestBuild`) and `freightCreationPolicy` (`Automatic|Manual`); Freight is
a fixed snapshot; a Stage's `requestedFreight.sources` is either a Warehouse (direct) or upstream
Stages, with `requiredSoakTime`/`availabilityStrategy`; Promotions run `steps` (`git-clone`,
`kustomize-set-image`, `git-push`, `git-open-pr`, `git-wait-for-pr`, `argocd-update`,
`argocd-wait`); verification uses `AnalysisTemplates` (Argo Rollouts CRDs: Prometheus/Datadog/Web)
and only a Successful AnalysisRun marks Freight verified.

| Check | Command | Flags a |
|---|---|---|
| Schema | `kubeconform -summary $CHANGED` (or `kubectl --dry-run=server`) | invalid manifest |
| Org policy | `conftest test $CHANGED` (OPA) | policy violation |
| Secrets | `gitleaks detect --no-banner --redact` | plaintext credential |

grep tells the scanners miss: `verification:`/`analysisTemplates:` presence on prod Stages;
`argocd-update`/`argocd-wait` in promotion steps; `git-open-pr`+`git-wait-for-pr` on prod;
`sources.warehouse` directly on a prod stage; `imageSelectionStrategy: Digest` with a mutable
tag or `NewestBuild` auto-promotion; `requiredSoakTime`/rollback on canary/blue-green;
`kind: Secret` with plaintext `data` (not `SealedSecret`/`ExternalSecret`).

## 3. Blocking bar
Set `blocking: true` ONLY for: a prod Stage with no verification AnalysisTemplate (Freight
reaches prod ungated); a promotion with no `argocd-update` health gate (note Stage health is
composite — other Apps/failed Promotions also affect it); a prod Stage sourcing a Warehouse
DIRECTLY (stage-skip) or `availabilityStrategy != All`; unpinned Freight (Digest on a mutable
tag, or `NewestBuild`/auto `freightCreationPolicy` auto-promoting to prod); a prod promotion with
no human gate (missing `git-open-pr` + `git-wait-for-pr`); a canary/blue-green Stage with no
rollback or soak (no `requiredSoakTime`); plaintext Secrets in manifests. ADVISORY (reviewer
inference, not a Kargo-enforced guarantee): 'manual image edits committed to Git bypass the
Warehouse/Freight provenance' — Kargo relies on Git-as-source-of-truth + branch protection, so
flag it advisory, not blocking. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/deployment-juror.json`, `ran[]`/`skipped[]` honest.
`id` = `dep-<check>-<file>:<line>`. Nothing outside the JSON.
