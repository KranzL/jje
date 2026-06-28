---
type: juror
lane: deploy
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 2
tags: [juror, deploy]
---
# deployment-juror

Lane [[deploy]] · model `sonnet` · reasoning-led · presets [[preset-deploy]] · [[preset-full]]

## Specialization
JJE juror (deploy). Reviews GitOps progressive-delivery changes only — Kargo Warehouse/Freight/Stage/Promotion/verification and Argo CD/Rollouts gates. Flags unverified promotions, stage-skipping, unpinned freight, and missing rollback. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 2 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/deployment-juror.md`](../../.claude/agents/jurors/deployment-juror.md)
- Skill: [`.claude/skills/deployment-review/SKILL.md`](../../.claude/skills/deployment-review/SKILL.md)

## Why it exists
[[kargo-deployment]]
