---
type: juror
lane: code
model: haiku
tool_backed: false
scale_recall: caught
scale_false_alarms: 0
tags: [juror, code]
---
# observability-juror

Lane [[code]] · model `haiku` · reasoning-led · presets [[preset-code-full]] · [[preset-full]]

## Specialization
JJE juror. Reviews the candidate for logging, metrics, tracing, and error-path coverage only. Pattern checks over changed files. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/observability-juror.md`](../../.claude/agents/jurors/observability-juror.md)
- Skill: [`.claude/skills/observability-review/SKILL.md`](../../.claude/skills/observability-review/SKILL.md)

## Why it exists
[[jje-loop]]
