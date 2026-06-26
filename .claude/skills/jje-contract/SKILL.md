---
name: jje-contract
description: The JJE verdict contract. The exact JSON shape every juror emits and the field rules the Judge and the oscillation guard depend on. Preloaded into every juror and the Judge.
user-invocable: false
---

# JJE verdict contract

Every juror emits **exactly one JSON object and nothing else** — no prose before
or after. Prose verdicts turn aggregation to mush; this shape lets the Judge and
the oscillation guard gate deterministically.

```json
{
  "juror": "security-juror",
  "category": "security",
  "findings": [
    {
      "id": "sec-go.lang.security.audit.sqli-handler.go:142",
      "check": "semgrep:go.lang.security.audit.sqli",
      "severity": "error",
      "blocking": true,
      "issue": "User input concatenated into SQL in handler.go:142",
      "evidence": "semgrep go.lang.security.audit.sqli @ handler.go:142",
      "suggested_fix": "Parameterize via sqlx.NamedExec"
    }
  ],
  "ran": ["gitleaks", "semgrep", "govulncheck"],
  "skipped": []
}
```

## Field rules
- `juror` / `category` — your juror name and lane. Stay in your lane; say nothing
  about other lanes.
- `findings[]` — empty array if you found nothing. Each finding:
  - `id` — **stable and deterministic**: `<lane>-<check>-<file>:<line>`. Do NOT
    use timestamps or run counters. The oscillation guard recognizes a recurring
    finding by identity, so the same defect must produce the same id shape across
    iterations.
  - `check` — the tool/rule identifier (e.g. `semgrep:<rule>`, `pytest:<nodeid>`,
    `ruff:<code>`). The guard keys identity on `category + check + file +
    normalized issue`; keep `check` stable for the same defect.
  - `severity` — `info | warn | error`.
  - `blocking` — a SEPARATE boolean from severity, so the Judge gates without
    interpreting severity semantics. Only set `true` when the finding meets your
    lane's documented blocking bar.
  - `issue` — one sentence, include `file:line`.
  - `evidence` — REQUIRED for any tool-backed finding (rule id, failing test
    name, the line). **A finding with no evidence is advisory and must not be
    `blocking: true`.**
  - `suggested_fix` — the smallest change that clears it.
- `ran[]` / `skipped[]` — which checks you actually executed vs skipped (e.g. a
  tool not installed). A juror that skipped its CORE check has not really
  reviewed; report it honestly so the Judge can weigh or escalate. **Never infer
  what an un-run check would have found.**

Write the object to `iterations/iter-<n>/verdicts/<juror>.json`. Nothing else.
