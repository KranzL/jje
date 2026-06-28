---
type: juror
lane: pipeline
model: haiku
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, pipeline]
---
# data-quality-juror

Lane [[pipeline]] · model `haiku` · tool-backed · presets [[preset-pipeline]] · [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror. Reviews pipeline changes for nulls, dedup, and referential integrity only. Runs dbt test / data tests. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/data-quality-juror.md`](../../.claude/agents/jurors/data-quality-juror.md)
- Skill: [`.claude/skills/data-quality-review/SKILL.md`](../../.claude/skills/data-quality-review/SKILL.md)

## Why it exists
[[jje-loop]]
