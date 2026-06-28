---
type: juror
lane: machine-learning
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, machine-learning]
---
# ml-reproducibility-juror

Lane [[machine-learning]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-ml]]

## Specialization
JJE juror (machine-learning). Reviews ML reproducibility — seeds, pinned inputs/environment, and artifact lineage. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/ml-reproducibility-juror.md`](../../.claude/agents/jurors/ml-reproducibility-juror.md)
- Skill: [`.claude/skills/ml-reproducibility-review/SKILL.md`](../../.claude/skills/ml-reproducibility-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
