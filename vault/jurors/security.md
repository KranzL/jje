---
type: juror
lane: code
model: sonnet
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, code]
---
# security-juror

Lane [[code]] · model `sonnet` · tool-backed · presets [[preset-quick]] · [[preset-code-full]] · [[preset-security-sweep]] · [[preset-go]] · [[preset-iac]] · [[preset-deploy]] · [[preset-full]]

## Specialization
JJE juror. Audits the candidate for injection, secrets, authz gaps, and unsafe dependencies only. Tool-backed. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/security-juror.md`](../../.claude/agents/jurors/security-juror.md)
- Skill: [`.claude/skills/security-review/SKILL.md`](../../.claude/skills/security-review/SKILL.md)

## Why it exists
[[jje-loop]]
