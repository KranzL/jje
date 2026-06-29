---
name: security-review
description: The security juror's checklist and exact commands — gitleaks, semgrep, language SAST, dependency audit — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Security review

You review ONLY the security surface: injection, committed secrets, authz gaps, unsafe crypto, disabled TLS, unsafe dependencies (OWASP Top 10 2021; CWE Top 25 2023). Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only `$CHANGED` and what they touch. Detect the ecosystem from lockfiles:
`go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python,
`Cargo.toml` → Rust.

## 2. Context to load
Before running tools, read from the repo: what roles/privileges exist, how authz is enforced, and what the trust boundary is for each entry point (HTTP, queue, CLI). Enumerate new endpoints/handlers against OWASP ASVS v4.0 Chapter 4 access-control requirements — IDOR (numeric resource ID without ownership check) and vertical privilege escalation (role assumed without re-validation) are caught systematically, not by accident. For any new registry dependency in package.json/pyproject.toml/go.mod, check for typosquatting: name nearly matching a well-known package or author with zero public history.

## 3. Run the checks (gate each on `command -v`; absent → `skipped[]` + one `info` finding; never infer)

| Check | Command | Flags |
|---|---|---|
| Secrets | `gitleaks detect --no-banner --redact -v` | committed credential, key, token |
| SAST (all) | `semgrep --error --config auto $CHANGED` | injection, SSRF, deserialization, path traversal |
| SAST Go | `gosec ./...` | Go-specific unsafe patterns |
| SAST Python | `bandit -r $CHANGED` | Python-specific unsafe patterns |
| Deps Go | `govulncheck ./...` | known CVE in a used dependency |
| Deps Python | `pip-audit` | known CVE |
| Deps Rust | `cargo audit` | known CVE |
| Deps JS/TS | `npm audit --audit-level=high` | known CVE ≥ HIGH |

Grep the diff for tells the scanners miss:
- SQL injection: string-built queries — `+ user`, f-string/`%`/`.format` into a query (CWE-89)
- Command injection: `os.system(`, `os.popen(`, `shell=True` with interpolated variables (CWE-78)
- Deserialization: `pickle.loads(`, `yaml.load(` without `Loader=yaml.SafeLoader`, `marshal.loads(` on untrusted input (CWE-502)
- Template injection: `Template(` on user input, dynamically-built `.render(` (CWE-94)
- Weak password hash: `hashlib.md5(`, `hashlib.sha1(` for credential storage — bcrypt/argon2/scrypt required (CWE-916)
- Weak PRNG: `random.random(`, `Math.random(` for security tokens or session IDs (CWE-338)
- JWT misuse: `algorithms=["none"]`, validator accepting RS256 and HS256 together (key-confusion, CWE-347)
- Disabled TLS: `InsecureSkipVerify: true`, `requests.get(..., verify=False)`, `CURLOPT_SSL_VERIFYPEER` set to `0`
- Hardcoded credentials: literal passwords/API keys in source
- Authz gap: new HTTP handler or privileged function with no authz call

## 4. Blocking bar
Set `blocking: true` (cite file:line plus tool finding or grep match) ONLY for:
- A committed secret (any credential, key, or token found by gitleaks or grep)
- An injection reachable from untrusted input: SQL, command, template, deserialization, eval/exec (OWASP A03:2021; CWE-89, CWE-78, CWE-94, CWE-502)
- A known CVE with NVD CVSSv3 CRITICAL (≥9.0): hard block; HIGH (≥7.0): blocking by default — document an escape hatch only when the affected code path is provably unreachable in this deployment
- Disabled TLS verification (`InsecureSkipVerify: true`, `verify=False`, `CURLOPT_SSL_VERIFYPEER=0`) — exposes all traffic to MITM
- A new privileged endpoint or handler with no authz check (OWASP A01:2021; ASVS v4.0 Chapter 4)
Everything else is advisory (`warn`/`info`, `blocking: false`). A finding with no tool/grep evidence is advisory by rule.

## 5. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/security-juror.json`. Put what you ran in `ran[]`,
what you couldn't in `skipped[]`. `id` = `sec-<check>-<file>:<line>`. Nothing
outside the JSON.
