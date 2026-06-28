---
type: juror
lane: pipeline
model: sonnet
tool_backed: true
scale_recall: MISS
scale_false_alarms: 0
tags: [juror, pipeline]
---
# data-contract-juror

Lane [[pipeline]] · model `sonnet` · tool-backed · presets [[preset-pipeline]] · [[preset-security-sweep]] · [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror. Reviews pipeline changes for schema evolution and event-contract compatibility only. Runs dbt parse/compile. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | MISS | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/data-contract-juror.md`](../../.claude/agents/jurors/data-contract-juror.md)
- Skill: [`.claude/skills/data-contract-review/SKILL.md`](../../.claude/skills/data-contract-review/SKILL.md)

## Why it exists
[[jje-loop]]
