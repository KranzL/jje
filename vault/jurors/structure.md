---
type: juror
lane: code
model: haiku
tool_backed: true
scale_recall: caught
scale_false_alarms: 0
tags: [juror, code]
---
# structure-juror

Lane [[code]] · model `haiku` · tool-backed · presets [[preset-code-full]] · [[preset-full]]

## Specialization
JJE juror. Reviews the candidate for naming, module boundaries, and repo conventions only. Runs the linter. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/structure-juror.md`](../../.claude/agents/jurors/structure-juror.md)
- Skill: [`.claude/skills/structure-review/SKILL.md`](../../.claude/skills/structure-review/SKILL.md)

## Why it exists
[[jje-loop]]
