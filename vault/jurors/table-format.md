---
type: juror
lane: datalake
model: sonnet
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, datalake]
---
# table-format-juror

Lane [[datalake]] · model `sonnet` · tool-backed · presets [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror (datalake). Reviews lakehouse table-format changes only — Iceberg/Delta/Hudi schema evolution, partition-spec evolution, snapshot/time-travel, and ACID/commit semantics. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/table-format-juror.md`](../../.claude/agents/jurors/table-format-juror.md)
- Skill: [`.claude/skills/table-format-review/SKILL.md`](../../.claude/skills/table-format-review/SKILL.md)

## Why it exists
[[lakehouse]]
