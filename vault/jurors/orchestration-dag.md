---
type: juror
lane: data-platforms
model: sonnet
tool_backed: false
scale_recall: caught
scale_false_alarms: 1
tags: [juror, data-platforms]
---
# orchestration-dag-juror

Lane [[data-platforms]] · model `sonnet` · reasoning-led · presets [[preset-full]] · [[preset-data-platforms]]

## Specialization
JJE juror (data-platforms). Reviews pipeline orchestration control plane — idempotency, determinism, backfill/catchup safety. Principal-level. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | caught | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/orchestration-dag-juror.md`](../../.claude/agents/jurors/orchestration-dag-juror.md)
- Skill: [`.claude/skills/orchestration-dag-review/SKILL.md`](../../.claude/skills/orchestration-dag-review/SKILL.md)

## Why it exists
[[principal-data-jurors]]
