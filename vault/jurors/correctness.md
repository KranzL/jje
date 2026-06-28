---
type: juror
lane: code
model: sonnet
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, code]
---
# correctness-juror

Lane [[code]] · model `sonnet` · tool-backed · presets [[preset-quick]] · [[preset-code-full]] · [[preset-go]] · [[preset-full]]

## Specialization
JJE juror. Reviews the candidate for logic, edge cases, and complexity only. Runs the test suite and reasons about correctness. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/correctness-juror.md`](../../.claude/agents/jurors/correctness-juror.md)
- Skill: [`.claude/skills/correctness-review/SKILL.md`](../../.claude/skills/correctness-review/SKILL.md)

## Why it exists
[[jje-loop]]
