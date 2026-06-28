---
type: juror
lane: data-science
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, data-science]
---
# statistical-rigor-juror

Lane [[data-science]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-science]]

## Specialization
JJE juror (data-science). Reviews statistical inferential validity — multiplicity, power, peeking, aggregation artifacts. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/statistical-rigor-juror.md`](../../.claude/agents/jurors/statistical-rigor-juror.md)
- Skill: [`.claude/skills/statistical-rigor-review/SKILL.md`](../../.claude/skills/statistical-rigor-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
