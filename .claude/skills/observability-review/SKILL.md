---
name: observability-review
description: The observability juror's checklist and exact grep patterns for logging, metrics, tracing, and error-path coverage on new code paths.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

# observability review
You review ONLY the observability surface: logging, metrics, tracing, and error-path coverage on NEW code paths. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Run the checks
This lane is mostly reasoning over the diff; no external tool is required. Identify each NEW surface in $CHANGED: a request handler, a background job, an outbound call. For each surface confirm BOTH error handling AND some instrumentation are present.

| Check | Command | Flags |
|-------|---------|-------|
| Logging present | `grep -nE 'logger\|log\.\|logging\.' <file>` | -nE |
| Tracing/spans | `grep -nE 'span\|trace\|tracer' <file>` | -nE |
| Metrics | `grep -nE 'metric\|counter\|histogram\|gauge' <file>` | -nE |
| Error handling | `grep -nE 'try\|except\|catch\|if err != nil\|Result<\|\?' <file>` | -nE |

For any external tool you choose to invoke, run `command -v <tool>` first. If absent, add to skipped[] and emit one info/non-blocking finding "check skipped: <tool> not installed". Never infer what an un-run check would have found.

## 3. Blocking bar
Set blocking:true ONLY for: a NEW surface (handler, job, external call) that ships with no error handling OR no instrumentation. An existing path missing a metric is advisory. Everything else advisory. A finding with no evidence is advisory by rule.

## 4. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/observability-juror.json. ran[]/skipped[] honest. id = obs-<check>-<file>:<line>. Nothing outside the JSON.
