---
name: deployment-review
description: The deployment juror's checklist and exact commands for GitOps progressive-delivery and promotion safety across Kargo and Argo CD / Argo Rollouts.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Deployment review

You review ONLY GitOps progressive-delivery / promotion safety — Kargo (Warehouse, Freight, Stage, Promotion, verification) and Argo CD / Argo Rollouts gates. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD -- '*.yaml' '*.yml')"
```
Detect Kargo/Argo manifests: `kind:` of `Warehouse|Stage|Promotion|Project`, Argo CD `Application`, or `AnalysisTemplate`. Reason over each as YAML.

## 2. Context to load
Read the Stage graph from the diff to identify the prod Stage name — the blocking bar applies only to prod; without this mapping findings are unanchored. Then read: every AnalysisTemplate referenced by a prod Stage (check `metrics[]` non-empty and `successCondition` non-trivial); Argo CD Applications for workloads in scope (`spec.syncPolicy.automated`, `prune:`); PodDisruptionBudgets for any workload whose Rollout is changed (PDB absent or `minAvailable: 0` lets Argo CD composite health falsely report Healthy while all pods drain).

## 3. Run the checks (gate every tool on `command -v`; missing → `skipped[]` + one info finding; never infer)
VERIFIED Kargo model: Warehouse `imageSelectionStrategy` (`SemVer|Lexical|Digest|NewestBuild`); Stage `spec.verification.requiredSoakTime` (soak dwell time, not inside `requestedFreight.sources`); Promotion `steps` include `git-open-pr`/`git-wait-for-pr`/`argocd-update`/`argocd-wait`; verification via `AnalysisTemplates` (Argo Rollouts CRDs — only a Successful AnalysisRun marks Freight verified). Argo Rollouts canary API: `steps[].setWeight` cumulative toward 100; analysis or pause steps must interleave with weight increments — analysis only at the end means the ramp proceeds ungated.

| Check | Command | Flags |
|---|---|---|
| Schema | `kubeconform -summary $CHANGED` (or `kubectl --dry-run=server`) | invalid manifest |

Grep tells: `requiredSoakTime:` absent or value < `5m` on canary/blueGreen Stage; `metrics:` empty list in AnalysisTemplate; `successCondition:` trivially passing zero (`result >= 0`); `setWeight:` > `20` with no `analysis:` immediately after; `autoPromotionEnabled: true`; nested `automated:` under `syncPolicy:` on a prod Application; `prune: true`; `minAvailable: 0` or no PDB on Rollout workload.

## 4. Blocking bar
Set `blocking: true` ONLY for (cite file:line):
- Prod Stage with no `verification.analysisTemplates` entry — Freight reaches prod ungated.
- Prod Stage AnalysisTemplate with `metrics: []` or `successCondition` trivially passing zero/null (e.g. `result >= 0`) — gate is hollow.
- `requiredSoakTime` absent or < `5m` on a canary or blueGreen prod Stage — no real dwell.
- Promotion missing `argocd-update` + `argocd-wait` in its `steps` — health never confirmed.
- Prod promotion missing `git-open-pr` + `git-wait-for-pr` (no human gate).
- `blueGreen.autoPromotionEnabled: true` with no `prePromotionAnalysis`/`postPromotionAnalysis` — ungated flip.
- Canary `steps` with `analysis` entries only after all weight steps, or any single `setWeight` > 20 with no following analysis/pause — ramp proceeds ungated.
- Prod Argo CD Application with `spec.syncPolicy.automated` set and no approved `syncWindow` — bypasses Kargo Freight/Promotion chain entirely.
- `spec.syncPolicy.automated.prune: true` on any non-ephemeral Application — silently deletes live resources when Git diverges.
- PDB absent or `minAvailable: 0` for a workload whose Rollout spec is changed — composite health falsely Healthy during drain.

Everything else is advisory: manual image edits committed to Git (branch protection is the real gate; flag advisory not blocking); canary soak ≥ 5m with no explicit rollback trigger; ApplicationSet generator fan-out without per-cluster `syncWindow` (flag with cluster count). A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- `spec.syncPolicy.automated` with `selfHeal: true` and/or `prune: true` on a prod Application — Kargo gate bypassed; `prune: true` also silently deletes live resources on Git divergence.
- `blueGreen.autoPromotionEnabled: true` with no `prePromotionAnalysis`/`postPromotionAnalysis` — ungated blue-green flip.
- Canary `steps` where `analysis` appears only as the final step — ramp proceeds 0 → ~100% ungated.
- Single `setWeight: 100` or any `setWeight` > 20 with no following analysis/pause step — big-bang deploy disguised as a canary.
- AnalysisTemplate `metrics: []` or `successCondition: 'result >= 0'` — analysis CRD present, gate hollow.
- PDB absent or `minAvailable: 0` on the Rollout workload — all pods drain while Stage reports Healthy.

## 6. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to `iterations/iter-<n>/verdicts/deployment-juror.json`, `ran[]`/`skipped[]` honest. `id` = `dep-<check>-<file>:<line>`. Nothing outside the JSON.
