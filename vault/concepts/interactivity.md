---
type: concept
tags: [concept, interactivity]
---
# Interactivity (human-in-the-loop)

The [[jje-loop|Planner/Executor/Judge]] are subagents and cannot prompt the user,
so questioning is **orchestrator-brokered**: each role returns its open questions
and the orchestrator asks via `AskUserQuestion`, then feeds the answers back.

- **Planner** → `questions_for_user` (scope, approach forks, success criteria).
- **Executor** → `decisions_needed` at real implementation forks (stops, doesn't guess).
- **Judge** → `clarifications` on judgment-dependent routes (REVISE vs REPLAN).

Configurable: `interactivity.level` = `minimal` / `normal` / **`high`** (default)
/ `max`. `minimal` keeps unattended/CI runs autonomous; the hard
`recommend_escalate` backstop is never overridable.

Skill: [`.claude/skills/jje/SKILL.md`](../../.claude/skills/jje/SKILL.md) (§Interactivity).
