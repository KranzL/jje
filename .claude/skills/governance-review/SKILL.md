---
name: governance-review
description: The governance juror's checklist and exact commands for ownership, PII handling, and catalog/lineage registration.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# governance review
You review ONLY ownership, PII handling, and catalog/lineage registration. PRINCIPAL level. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Reference canon
- **GDPR Regulation (EU) 2016/679 Art. 4(1)** — definition of personal data; **Art. 9** — special-category data requiring heightened controls: health, biometric, genetic, racial/ethnic origin, religious/philosophical beliefs, political opinions, trade-union membership, sexual orientation.
- **HIPAA Safe Harbor 45 CFR §164.514(b)** — 18 PHI identifiers: names, geographic sub-state, dates (except year), phone, fax, email, SSN, MRN, health-plan beneficiary number, account numbers, certificate/license numbers, VINs, device identifiers, URLs, IP addresses, biometric identifiers, full-face photographs, any other unique identifier.
- **PCI-DSS v4.0 Requirement 3** — account data scope: CHD (PAN, cardholder name, expiration date, service code); SAD (CVV/CVV2, full track data); display rule first 6/last 4 for PAN; storage of SAD post-authorization is prohibited.
- **OpenLineage** (Linux Foundation) — open standard for lineage exchange; RunEvent is the interop unit; facets (RunFacet, JobFacet, DatasetFacet, InputDatasetFacet, OutputDatasetFacet) are extension points; ingested by DataHub, OpenMetadata, Marquez, dbt Cloud.
- **dbt column meta/tags** — `meta.masking_policy` wires to a Snowflake dynamic data masking policy; BigQuery column-level security uses `policy_tags` in schema yml.

**Governed-tier definition** (the only criteria accepted here): a model is governed-tier if any column matches GDPR personal data (Art. 4(1)), HIPAA PHI (§164.514(b) 18-identifier list), or PCI-DSS account data (CHD or SAD), or its schema is designated regulated in project conventions.

## 3. Run the checks
Reasoning over yml/config/SQL; no external scanner required. Gate any tool on `command -v`; absent → skipped[] + one info finding; never infer.

PII pattern (substitute inline): `email|ssn|social_sec|\bphone\b|\bfax\b|address|first_name|last_name|\bdob\b|\bbirth\b|\bmrn\b|\bip\b|\blat\b|\blon\b|credit_card|passport|national_id|driver_lic|tax_id|account_num|routing|biometric|diagnosis|health_cond|\bsalary\b|\brace\b|religion`

| Check | Command |
| --- | --- |
| PII column scan | `grep -rniE '$PII_PATTERN' $CHANGED` |
| PII in log/error sinks | `grep -rniE 'log(ger)?\.(info\|warn\|error\|debug).*(email\|ssn\|name\|phone\|dob)\|print.*ssn' $CHANGED` |
| PII in seeds/test fixtures | `grep -rniE '$PII_PATTERN' seeds/ tests/` |
| Masking tag present | `grep -niE 'tags:\|meta:\|pii\|mask\|classify\|policy_tag' $CHANGED` |
| Masking enforced at warehouse | `grep -niE 'MASKING POLICY\|policyTags\|masking_policy\|column_masking' $CHANGED` |
| Named owner | `grep -niE 'owner:\|meta.*owner\|CODEOWNERS' $CHANGED` — must resolve to email, team alias, or @GitHub handle; `owner: tbd` or blank is not a named owner |
| Retention/deletion SLA | `grep -niE 'retention\|ttl\|delete_after\|expire\|purge' $CHANGED` — required for PII-bearing models (GDPR Art. 5(1)(e)) |
| Lineage registration | `grep -niE 'openlineage\|datahub\|openmetadata\|marquez\|meta.*owner' $CHANGED` |

For every new/changed column matching the PII pattern: confirm tag present AND warehouse masking policy present. For governed-tier models: confirm named owner and a resolvable lineage entry (OpenLineage RunEvent emission, catalog ingestion config, or dbt exposure reference).

## 4. Blocking bar
Set blocking:true (cite file:line, the column or field, the regulation) ONLY for:
- A new or changed column matching the PII pattern with no masking tag AND no warehouse-layer masking policy (Snowflake `MASKING POLICY`, BigQuery `policyTags`, dbt `masking_policy`).
- A governed-tier model with no named owner resolving to a real identity.
- PII confirmed in a log/error sink, seed file, or test fixture — a copy that bypasses all masking controls.
- A governed-tier model with no resolvable lineage/catalog entry (OpenLineage RunEvent emission, DataHub/OpenMetadata/Marquez ingestion config, or dbt exposure reference).
Everything else is advisory. A finding with no evidence is advisory by rule.

## 5. Anti-patterns to hunt
- PII column (GDPR Art. 4(1) / HIPAA §164.514(b)) present with no tag AND no warehouse masking policy — the most common real-world violation path.
- Masking tag present in yml but no masking policy object wired at the warehouse layer — tag theatre; the data is still exposed.
- PII field name in a log/print/debug statement — bypasses all warehouse-layer controls regardless of column tagging.
- PII values in seeds/ or test fixture files — committed raw data, typically outside access controls.
- `owner: tbd` or empty owner on a governed-tier model — unenforceable accountability.
- Governed-tier model absent from the lineage graph — no downstream impact visibility, blocks incident response.
- Full PAN stored beyond first 6/last 4 display rule (PCI-DSS v4.0 Req 3) — prohibited cardholder data retention.
- GDPR Art. 9 special-category data (health, biometric, racial origin, religion) with the same masking controls as ordinary personal data — Art. 9 requires explicit legal basis and heightened controls beyond standard PII masking.
- No retention/deletion SLA on a PII-bearing table — violates GDPR Art. 5(1)(e) storage-limitation principle.

## 6. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/governance-juror.json. ran[]/skipped[] honest. id = gov-<check>-<file>:<line>. Nothing outside the JSON.
