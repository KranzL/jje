---
type: juror
lane: machine-learning
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 2
tags: [juror, machine-learning]
---
# model-serving-mlops-juror

Lane [[machine-learning]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-ml]]

## Specialization
JJE juror (machine-learning). Reviews model serving / MLOps — registry/versioning, safe rollout, rollback, train/serve consistency. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 2 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/model-serving-mlops-juror.md`](../../.claude/agents/jurors/model-serving-mlops-juror.md)
- Skill: [`.claude/skills/model-serving-mlops-review/SKILL.md`](../../.claude/skills/model-serving-mlops-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
