---
type: juror
lane: machine-learning
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, machine-learning]
---
# model-evaluation-juror

Lane [[machine-learning]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-ml]]

## Specialization
JJE juror (machine-learning). Reviews ML model evaluation — metric choice, validation strategy, and trustworthy reported numbers. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/model-evaluation-juror.md`](../../.claude/agents/jurors/model-evaluation-juror.md)
- Skill: [`.claude/skills/model-evaluation-review/SKILL.md`](../../.claude/skills/model-evaluation-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
