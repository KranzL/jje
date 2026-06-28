---
type: juror
lane: datalake
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, datalake]
---
# partitioning-layout-juror

Lane [[datalake]] · model `sonnet` · reasoning-led · presets [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror (datalake). Reviews physical layout only — partition design, the small-files problem, file sizing, compaction, and clustering/Z-order. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/partitioning-layout-juror.md`](../../.claude/agents/jurors/partitioning-layout-juror.md)
- Skill: [`.claude/skills/partitioning-layout-review/SKILL.md`](../../.claude/skills/partitioning-layout-review/SKILL.md)

## Why it exists
[[lakehouse]]
