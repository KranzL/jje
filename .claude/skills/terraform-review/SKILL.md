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

## 2. Context to load
Read before running checks — org-specific violations are invisible without them:
- `policy/` OPA/Rego files: know what `conftest` will gate before running it; treat any `.jje/conventions` blocking rules as additional blocking bars.
- `*.tfvars` files: understand environment names and separation boundaries.
- Remote backend config: workspace-per-env vs. separate state files changes what env isolation means.
- `.terraform.lock.hcl`: confirm it is committed (`git ls-files | grep .terraform.lock.hcl`); absence on a repo with real provider blocks is a blocking finding.

## 3. Run the checks (gate each external tool on `command -v`; missing -> `skipped[]` + one `info` finding; never infer)
IMPORTANT: `tfsec` is DEPRECATED (merged into Trivy) — do NOT use it; use `trivy config` + `checkov`.

| Check | Command | Flags |
|---|---|---|
| Formatting | `terraform fmt -check -recursive` | drift from canonical style |
| Syntax/consistency | `terraform init -backend=false && terraform validate` | invalid config (blocking gate) |
| Plan evidence | `terraform plan -out=tfplan.binary && terraform show -json tfplan.binary > tfplan.json` | real created/modified resources; no backend -> raw-HCL scan, mark plan-derived checks `skipped` |
| Misconfig (deep) | `checkov -d . --compact --quiet --severity HIGH` (or `checkov -f tfplan.json`) | CIS AWS v3.0 + AWS FSBP controls; graph-aware |
| Misconfig (breadth) | `trivy config --severity HIGH,CRITICAL .` | inherits tfsec rules |
| Lint | `tflint --init && tflint --recursive` | provider errors, deprecated syntax, invalid instance types (LINTER only, not a scanner) |
| Policy | `conftest test tfplan.json -p policy/` | org OPA/Rego guardrails (if `policy/` exists) |
| Cost | `infracost breakdown --path=. --out-file=base.json` (from main) then `infracost diff --compare-to=base.json` | PR cost delta |

Manual grep tells the scanners miss: `0.0.0.0/0` or `::/0` ingress; `publicly_accessible = true`;
hardcoded `secret/password/access_key/private_key = "..."`; IAM/principal `"*"` wildcard;
`acl = "public-*"`; unpinned `version = ">..."` ranges; committed state (`git ls-files | grep tfstate`);
missing `backend "s3|remote|gcs|azurerm"`; `backend "s3"` lacking `dynamodb_table`;
`aws_instance`/`aws_launch_template` lacking `metadata_options { http_tokens = "required" }` (CKV_AWS_79);
`aws_kms_key` lacking `enable_key_rotation = true` (CKV_AWS_7);
`local-exec`/`remote-exec` provisioner blocks; module `source` `?ref=` pointing to branch not tag/SHA.

## 4. Blocking bar
Set `blocking: true` ONLY for: public S3 (Principal `"*"` / public ACL / missing `aws_s3_bucket_public_access_block`);
SG ingress from `0.0.0.0/0`|`::/0` on sensitive ports (22/3389/3306/5432/6379/27017 or all `-1`);
unencrypted-at-rest on a plan that creates/modifies (EBS `encrypted`, RDS `storage_encrypted`, S3 SSE);
over-permissive IAM (Action `"*"`/`service:*` with Resource `"*"`; `AdministratorAccess`);
public RDS (`publicly_accessible = true`); plaintext secrets in `.tf`/`.tfvars`; `terraform validate`
failure; committed `*.tfstate`; S3 backend without `dynamodb_table` (concurrent applies corrupt state);
`.terraform.lock.hcl` absent from a repo with real provider blocks; unpinned providers/modules;
IMDSv2 not enforced (`http_tokens = "required"` absent on `aws_instance`/`aws_launch_template`, CKV_AWS_79);
KMS key rotation disabled (`enable_key_rotation = true` absent on `aws_kms_key`, CKV_AWS_7).

**Scanner-required rule.** If `$CHANGED` contains real AWS resources AND **neither `checkov` nor `trivy` ran**
(both in `skipped[]`), emit `blocking: true` finding `tf-unverifiable: IaC security cannot
be certified without a scanner — install checkov or trivy`.

ADVISORY: infracost increases (blocking only vs an explicit budget threshold); `count` on stateful
resources (`aws_db_instance`, `aws_ebs_volume`) — list-index shift on insertion triggers destroy/recreate,
prefer `for_each`; fmt/naming nits; low/medium-severity scanner findings; a non-security tool skipped.

## 5. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/terraform-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`, honest. `id` = `tf-<check>-<file>:<line>`. Nothing
outside the JSON.
