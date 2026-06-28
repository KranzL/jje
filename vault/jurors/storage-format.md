---
type: juror
lane: datalake
model: haiku
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, datalake]
---
# storage-format-juror

Lane [[datalake]] · model `haiku` · reasoning-led · presets [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror (datalake). Reviews file/storage format only — Parquet/ORC/Avro choice, compression codec, column encoding, and predicate-pushdown friendliness. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/storage-format-juror.md`](../../.claude/agents/jurors/storage-format-juror.md)
- Skill: [`.claude/skills/storage-format-review/SKILL.md`](../../.claude/skills/storage-format-review/SKILL.md)

## Why it exists
[[lakehouse]]
