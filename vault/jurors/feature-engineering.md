---
type: juror
lane: machine-learning
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, machine-learning]
---
# feature-engineering-juror

Lane [[machine-learning]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-ml]]

## Specialization
JJE juror (machine-learning). Reviews ML feature engineering — point-in-time correctness and training/serving skew. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/feature-engineering-juror.md`](../../.claude/agents/jurors/feature-engineering-juror.md)
- Skill: [`.claude/skills/feature-engineering-review/SKILL.md`](../../.claude/skills/feature-engineering-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
