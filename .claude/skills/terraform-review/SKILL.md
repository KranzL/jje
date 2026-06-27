---
name: terraform-review
description: The AWS Terraform/IaC juror's checklist and exact commands — fmt/validate, trivy config, checkov, tflint, conftest, infracost, plus grep tells — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Terraform review

You review ONLY AWS Terraform / IaC: security misconfig, IAM least-privilege,
encryption, public exposure, state hygiene, version pinning, cost. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD -- '*.tf' '*.tfvars' '*.hcl')"
```
Detect the module layout, providers, and backend from `$CHANGED` and what they touch.

## 2. Run the checks (gate each external tool on `command -v`; missing -> `skipped[]` + one `info` finding; never infer)
IMPORTANT tool currency (verified): `tfsec` is DEPRECATED (merged into Trivy) and
`terrascan` is ARCHIVED — do NOT use them; use `trivy config` + `checkov`.

| Check | Command | Flags a |
|---|---|---|
| Formatting | `terraform fmt -check -recursive` | drift from canonical style |
| Syntax/consistency | `terraform init -backend=false && terraform validate` | invalid config (blocking gate) |
| Plan evidence | `terraform plan -out=tfplan.binary && terraform show -json tfplan.binary > tfplan.json` | real created/modified resources; no backend -> raw-HCL scan, mark plan-derived checks `skipped` |
| Misconfig (deep) | `checkov -d . --compact --quiet --check HIGH,CRITICAL` (or `checkov -f tfplan.json`) | graph-aware security/least-privilege |
| Misconfig (breadth) | `trivy config --severity HIGH,CRITICAL .` | inherits tfsec rules |
| Lint | `tflint --init && tflint --recursive` | provider errors, deprecated syntax, invalid instance types (LINTER only, not a scanner) |
| Policy | `conftest test tfplan.json -p policy/` | org OPA/Rego guardrails (if `policy/` exists) |
| Cost | `infracost breakdown --path=. --out-file=base.json` (from main) then `infracost diff --compare-to=base.json` | PR cost delta |

Manual grep tells the scanners miss: `0.0.0.0/0` or `::/0` ingress;
`publicly_accessible = true`; hardcoded `secret/password/access_key/private_key = "..."`;
IAM/principal `"*"` wildcard; `acl = "public-*"`; unpinned `version = ">..."` ranges;
committed state (`git ls-files | grep tfstate`); missing `backend "s3|remote|gcs|azurerm"`.

## 3. Blocking bar
Set `blocking: true` ONLY for: public S3 (Principal `"*"` / public ACL / missing
`aws_s3_bucket_public_access_block`); SG ingress from `0.0.0.0/0`|`::/0` on sensitive
ports (22/3389/3306/5432/6379/27017 or all `-1`); unencrypted-at-rest a plan
creates/modifies (EBS `encrypted`, RDS `storage_encrypted`, S3 SSE); over-permissive
IAM (Action `"*"`/`service:*` with Resource `"*"`; broad `AdministratorAccess`);
public RDS (`publicly_accessible = true`); plaintext secrets in `.tf`/`.tfvars`;
`terraform validate` failure; committed `*.tfstate` or no remote-locked backend;
unpinned providers/modules. ADVISORY: infracost increases (blocking only vs an
explicit budget threshold), count-vs-for_each style, fmt/naming nits,
low/medium-severity scanner findings, any tool skipped. No-evidence = advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/terraform-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`, honest. `id` = `tf-<check>-<file>:<line>`. Nothing
outside the JSON.
