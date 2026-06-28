---
type: research
tags: [research, agents]
verified: 2026-06
---
# Research: stronger agents

Current (2025-2026) best practice for multi-agent LLM review, mapped to JJE.

## Key findings
- **Correlated errors**: a panel of same-family LLM judges gives ~2 *effective*
  independent votes regardless of headcount; model-family diversity barely helps.
  → independence comes from [[tool-backing]], not juror count.
- Bias (verbosity/position/leniency) moved *off* the [[jje-loop|Judge]] (now a
  deterministic router — a strength) *onto* the jurors. → add anti-pattern
  criteria; never anchor on the Executor's self-report.
- **Self-correction illusion**: a finding clears only on a re-run with fresh
  evidence, not the juror agreeing it looks fixed.
- Model choice: security pattern-recognition is where small models miss → moved
  [[security]] to Sonnet.
- **Eval-driven development** is the missing instrument → led to [[scorecard|the
  eval]].

## Applied
self-report-advisory + anti-pattern hunting in the verdict contract; security →
Sonnet; the [[scorecard|3-pass eval]].

Sources: Anthropic effective-context-engineering + multi-agent-research; arXiv
2410.02736, 2404.18796, 2605.29800, 2506.11442; ACL 2025.findings-1141.
