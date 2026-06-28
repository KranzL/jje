---
type: juror
lane: data-science
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, data-science]
---
# causal-inference-juror

Lane [[data-science]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-science]]

## Specialization
JJE juror (data-science). Reviews causal-inference validity — confounding, collider/selection bias, unsupported causal claims. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/causal-inference-juror.md`](../../.claude/agents/jurors/causal-inference-juror.md)
- Skill: [`.claude/skills/causal-inference-review/SKILL.md`](../../.claude/skills/causal-inference-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
