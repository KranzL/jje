---
type: concept
tags: [concept, methodology]
---
# The JJE loop

The generator–critic methodology the whole harness implements: four roles, one
loop, one invariant.

- **Planner** turns a request into a plan (steps, files-in-scope, risks, explicit
  success criteria). Now also returns `questions_for_user` ([[interactivity]]).
- **Executor** builds the candidate on a scratch branch in an isolated worktree.
- **Jury** — a seated panel of independent, scoped, tool-backed reviewers (the
  [[MOC|38 jurors]]) that run in parallel and never see each other.
- **Judge** — a deterministic router over the verdicts: ACCEPT / REVISE / REPLAN
  / ESCALATE.

The **invariant**: the loop operates on a *candidate*, never mainline; nothing
ships until the Judge accepts and CI is green ([[safety-model]]). Termination is
guaranteed by an iteration budget + an oscillation guard.

The jury's value comes from [[tool-backing]], not headcount. Lanes are extended
with one agent + one skill + a config entry — see the [[MOC]] for the roster.

Spec: [`judge-jury-executioner.md`](../../judge-jury-executioner.md) ·
Architecture: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md)
