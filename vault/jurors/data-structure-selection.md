---
type: juror
lane: ds-and-algorithms
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, ds-and-algorithms]
---
# data-structure-selection-juror

Lane [[ds-and-algorithms]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-dsa]]

## Specialization
JJE juror (ds-and-algorithms). Reviews data-structure/index/sketch fit — exactness needs, access patterns, sized error budgets. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/data-structure-selection-juror.md`](../../.claude/agents/jurors/data-structure-selection-juror.md)
- Skill: [`.claude/skills/data-structure-selection-review/SKILL.md`](../../.claude/skills/data-structure-selection-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
