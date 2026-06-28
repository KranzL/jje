---
type: juror
lane: data-modeling
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, data-modeling]
---
# dimensional-modeling-juror

Lane [[data-modeling]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-modeling]]

## Specialization
JJE juror (data-modeling). Reviews Kimball dimensional design — grain, fact/dimension separation, additivity, conformed dimensions, SCD intent. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/dimensional-modeling-juror.md`](../../.claude/agents/jurors/dimensional-modeling-juror.md)
- Skill: [`.claude/skills/dimensional-modeling-review/SKILL.md`](../../.claude/skills/dimensional-modeling-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
