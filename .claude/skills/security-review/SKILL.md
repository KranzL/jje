---
name: security-review
description: The security juror's checklist and exact commands — gitleaks, semgrep, language SAST, dependency audit — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Security review

You review ONLY the security surface: injection, committed secrets, authz gaps,
unsafe dependencies. Four steps. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust.

## 2. Run the checks (gate each on the tool being installed)
For every tool: `command -v <tool>` first. If absent, add it to `skipped[]` and
emit one `info`/non-blocking finding "`check skipped: <tool> not installed`".
Never infer what an un-run check would have found.

| Check | Command | Flags a |
|---|---|---|
| Secrets | `gitleaks detect --no-banner --redact -v` (or `gitleaks protect --staged`) | committed credential, key, token |
| SAST (all) | `semgrep --error --config auto $CHANGED` | injection, SSRF, deserialization, path traversal |
| SAST Go | `gosec ./...` | Go-specific unsafe patterns |
| SAST Python | `bandit -r $CHANGED` | Python-specific unsafe patterns |
| Deps Go | `govulncheck ./...` | known CVE in a used dependency |
| Deps Python | `pip-audit` | known CVE |
| Deps Rust | `cargo audit` | known CVE |

Also grep the diff for the obvious manual tells the scanners miss: string-built
SQL (`+ user`, f-strings/`%`/`.format` into a query), `eval`/`exec` on input,
`shell=True` with interpolation, disabled TLS verification, hardcoded creds,
missing authz checks on a new endpoint/handler.

## 3. Blocking bar
Set `blocking: true` ONLY for: a committed secret; an injection reachable from
untrusted input; a known CVE (`error`-severity advisory) in a shipped dependency;
a new privileged endpoint with no authz check. Everything else is advisory
(`warn`/`info`, `blocking: false`). A finding with no tool/grep evidence is
advisory by rule.

## 4. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/security-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`. `id` = `sec-<check>-<file>:<line>`. Nothing
outside the JSON.
