---
type: concept
tags: [concept, safety]
---
# Safety model (two tiers)

JJE has two tiers of enforcement, and we **tested both**
([`docs/TEST-FINDINGS.md`](../../docs/TEST-FINDINGS.md)).

## Tier 1 — unconditional (does not depend on hooks)
- The candidate lives on a scratch branch in an isolated worktree; the
  orchestrator merges only after `accept` mints the marker. Even with every hook
  off, `main` stays clean if the orchestrator follows [[jje-loop|the skill]].
- CI is validated by a real exit-code artifact, not a model claim.
- The iteration budget is enforced by the `jje_state.py` CLI.

## Tier 2 — best-effort defense-in-depth (the hooks)
A `PreToolUse` gate blocks unapproved commits; a loop-guard caps Executor spawns.
**Conditional** — testing showed they enforce only when:
- the workspace is **trusted** (an untrusted workspace silently loads neither
  hooks nor permission rules), **and**
- the session is **not** in `bypassPermissions` mode (which ignores hook denials).

> [!contradiction] Earlier docs called the hooks "hard guarantees." The eval
> disproved that — they are conditional defense-in-depth. The unconditional
> guarantees are Tier 1. (Reframed in the README + the test findings doc.)

Scripts: [`.claude/hooks/`](../../.claude/hooks/) ·
[`.claude/scripts/jje_state.py`](../../.claude/scripts/jje_state.py)
