---
type: juror
lane: go
model: haiku
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, go]
---
# go-performance-juror

Lane [[go]] · model `haiku` · tool-backed · presets [[preset-go]] · [[preset-full]]

## Specialization
JJE juror (Go). Reviews Go performance only — allocations, escape analysis, unnecessary copies, benchmark regressions. Runs go test -bench and escape analysis. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/go-performance-juror.md`](../../.claude/agents/jurors/go-performance-juror.md)
- Skill: [`.claude/skills/go-performance-review/SKILL.md`](../../.claude/skills/go-performance-review/SKILL.md)

## Why it exists
[[jje-loop]]
