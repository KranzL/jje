---
type: juror
lane: code
model: sonnet
tool_backed: false
scale_recall: MISS
scale_false_alarms: 0
tags: [juror, code]
---
# interface-compat-juror

Lane [[code]] · model `sonnet` · reasoning-led · presets [[preset-code-full]] · [[preset-full]]

## Specialization
JJE juror. Reviews the candidate for public API / signature stability only. Diffs the published surface. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | MISS | 0 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/interface-compat-juror.md`](../../.claude/agents/jurors/interface-compat-juror.md)
- Skill: [`.claude/skills/interface-review/SKILL.md`](../../.claude/skills/interface-review/SKILL.md)

## Why it exists
[[jje-loop]]
