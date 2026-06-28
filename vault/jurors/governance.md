---
type: juror
lane: pipeline
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, pipeline]
---
# governance-juror

Lane [[pipeline]] · model `sonnet` · reasoning-led · presets [[preset-security-sweep]] · [[preset-full]]

## Specialization
JJE juror. Reviews pipeline changes for ownership, PII tagging, and catalog registration only. Scans for PII and owner tags. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/governance-juror.md`](../../.claude/agents/jurors/governance-juror.md)
- Skill: [`.claude/skills/governance-review/SKILL.md`](../../.claude/skills/governance-review/SKILL.md)

## Why it exists
[[jje-loop]]
