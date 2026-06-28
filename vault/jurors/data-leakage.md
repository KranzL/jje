---
type: juror
lane: machine-learning
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, machine-learning]
---
# data-leakage-juror

Lane [[machine-learning]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-ml]]

## Specialization
JJE juror (machine-learning). Reviews ML data leakage — train/test contamination, target leakage, temporal and entity leakage. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/data-leakage-juror.md`](../../.claude/agents/jurors/data-leakage-juror.md)
- Skill: [`.claude/skills/data-leakage-review/SKILL.md`](../../.claude/skills/data-leakage-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
