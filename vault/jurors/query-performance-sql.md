---
type: juror
lane: data-platforms
model: sonnet
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, data-platforms]
---
# query-performance-sql-juror

Lane [[data-platforms]] · model `sonnet` · tool-backed · presets [[preset-full]] · [[preset-data-platforms]]

## Specialization
JJE juror (data-platforms). Reviews SQL execution plan quality — join strategy, pruning-defeating predicates, skew. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/query-performance-sql-juror.md`](../../.claude/agents/jurors/query-performance-sql-juror.md)
- Skill: [`.claude/skills/query-performance-sql-review/SKILL.md`](../../.claude/skills/query-performance-sql-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
