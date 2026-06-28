---
type: juror
lane: data-modeling
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, data-modeling]
---
# normalization-relational-juror

Lane [[data-modeling]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-modeling]]

## Specialization
JJE juror (data-modeling). Reviews relational/normalization design — normal forms, keys, referential integrity, anomaly-free schema design. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/normalization-relational-juror.md`](../../.claude/agents/jurors/normalization-relational-juror.md)
- Skill: [`.claude/skills/normalization-relational-review/SKILL.md`](../../.claude/skills/normalization-relational-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
