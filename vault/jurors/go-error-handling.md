---
type: juror
lane: go
model: haiku
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, go]
---
# go-error-handling-juror

Lane [[go]] · model `haiku` · tool-backed · presets [[preset-go]] · [[preset-full]]

## Specialization
JJE juror (Go). Reviews Go error handling only — unchecked errors, error wrapping, sentinel errors, panic/recover misuse. Runs errcheck / golangci-lint. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/go-error-handling-juror.md`](../../.claude/agents/jurors/go-error-handling-juror.md)
- Skill: [`.claude/skills/go-error-handling-review/SKILL.md`](../../.claude/skills/go-error-handling-review/SKILL.md)

## Why it exists
[[jje-loop]]
