---
type: juror
lane: go
model: sonnet
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, go]
---
# go-concurrency-juror

Lane [[go]] · model `sonnet` · tool-backed · presets [[preset-go]] · [[preset-full]]

## Specialization
JJE juror (Go). Reviews Go concurrency only — data races, goroutine leaks, channel/mutex misuse, context cancellation. Runs go test -race and go vet. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/go-concurrency-juror.md`](../../.claude/agents/jurors/go-concurrency-juror.md)
- Skill: [`.claude/skills/go-concurrency-review/SKILL.md`](../../.claude/skills/go-concurrency-review/SKILL.md)

## Why it exists
[[jje-loop]]
