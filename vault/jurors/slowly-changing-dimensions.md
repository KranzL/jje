---
type: juror
lane: data-modeling
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, data-modeling]
---
# slowly-changing-dimensions-juror

Lane [[data-modeling]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-modeling]]

## Specialization
JJE juror (data-modeling). Reviews slowly-changing-dimension correctness — SCD types, history preservation, and as-of join correctness. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/slowly-changing-dimensions-juror.md`](../../.claude/agents/jurors/slowly-changing-dimensions-juror.md)
- Skill: [`.claude/skills/slowly-changing-dimensions-review/SKILL.md`](../../.claude/skills/slowly-changing-dimensions-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
