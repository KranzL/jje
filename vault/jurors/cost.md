---
type: juror
lane: pipeline
model: haiku
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, pipeline]
---
# cost-juror

Lane [[pipeline]] · model `haiku` · tool-backed · presets [[preset-pipeline]] · [[preset-full]]

## Specialization
JJE juror. Reviews pipeline changes for scan cost, partitioning, and file sizing only. Runs query EXPLAIN. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/cost-juror.md`](../../.claude/agents/jurors/cost-juror.md)
- Skill: [`.claude/skills/cost-review/SKILL.md`](../../.claude/skills/cost-review/SKILL.md)

## Why it exists
[[jje-loop]]
