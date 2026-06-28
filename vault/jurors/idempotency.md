---
type: juror
lane: pipeline
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, pipeline]
---
# idempotency-juror

Lane [[pipeline]] · model `sonnet` · reasoning-led · presets [[preset-pipeline]] · [[preset-datalake]] · [[preset-full]]

## Specialization
JJE juror. Reviews pipeline write semantics for idempotency, dedup, and merge correctness only. Reasons over the write path. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/idempotency-juror.md`](../../.claude/agents/jurors/idempotency-juror.md)
- Skill: [`.claude/skills/idempotency-review/SKILL.md`](../../.claude/skills/idempotency-review/SKILL.md)

## Why it exists
[[jje-loop]]
