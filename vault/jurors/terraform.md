---
type: juror
lane: iac
model: sonnet
tool_backed: true
scale_recall: MISS
scale_false_alarms: 1
tags: [juror, iac]
---
# terraform-juror

Lane [[iac]] · model `sonnet` · tool-backed · presets [[preset-iac]] · [[preset-full]]

## Specialization
JJE juror (IaC). Reviews AWS Terraform changes only — security misconfigurations, IAM least-privilege, encryption, state hygiene, version pinning, and cost. Runs Checkov / Trivy / tflint / Infracost / terraform validate. Emits one verdict.

## Eval scores
| Pass | Recall | Precision |
|---|---|---|
| Floor (canonical) | caught | quiet |
| Adversarial (disguised + decoy) | caught | quiet |
| Scale (buried in multi-file PR) | MISS | 1 false alarm(s) |

See [[scorecard]].

## Source (implementation)
- Agent: [`.claude/agents/jurors/terraform-juror.md`](../../.claude/agents/jurors/terraform-juror.md)
- Skill: [`.claude/skills/terraform-review/SKILL.md`](../../.claude/skills/terraform-review/SKILL.md)

## Why it exists
[[iac-terraform]]
