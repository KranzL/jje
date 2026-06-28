---
type: juror
lane: data-modeling
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, data-modeling]
---
# semantic-layer-metrics-juror

Lane [[data-modeling]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-modeling]]

## Specialization
JJE juror (data-modeling). Reviews semantic-layer metric correctness — additivity, fan-out/chasm traps, single-source-of-truth metric math. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/semantic-layer-metrics-juror.md`](../../.claude/agents/jurors/semantic-layer-metrics-juror.md)
- Skill: [`.claude/skills/semantic-layer-metrics-review/SKILL.md`](../../.claude/skills/semantic-layer-metrics-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
