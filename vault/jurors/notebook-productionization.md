---
type: juror
lane: data-science
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, data-science]
---
# notebook-productionization-juror

Lane [[data-science]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-science]]

## Specialization
JJE juror (data-science). Reviews notebook-to-production quality — reproducibility, parameterization, secrets, and tests. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/notebook-productionization-juror.md`](../../.claude/agents/jurors/notebook-productionization-juror.md)
- Skill: [`.claude/skills/notebook-productionization-review/SKILL.md`](../../.claude/skills/notebook-productionization-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
