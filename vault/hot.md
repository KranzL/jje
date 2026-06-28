---
type: hot-cache
updated: 2026-06-28
tags: [meta, hot-cache]
---
# Hot Cache — where did we leave off?

> Read this first. It is a ~500-word cache of current state, **overwritten each
> session**, not a journal. For the full map see [[MOC]].

## Last updated
**2026-06-28** — Built the Obsidian vault (this) over the JJE knowledge graph,
right after a three-pass juror eval.

## Key recent facts
- **JJE** is a generator–critic review harness for Claude Code (Planner →
  Executor → Jury → Judge), public at `github.com/KranzL/jje`. See [[jje-loop]].
- Roster is **38 jurors / 11 lanes / 14 presets**. The 20 newest are
  principal-level data lanes ([[principal-data-jurors]]).
- **The single biggest lever is tool-backing**, now proven empirically, not just
  argued — see [[tool-backing]] and [[scorecard]].
- **Eval ran three passes** ([[floor-eval]], [[adversarial-eval]],
  [[scale-eval]]): floor 38/38, adversarial 38/38, **scale 35/38 recall + 17
  false alarms**. The scale pass is the only one that could fail, and did.
- **The 3 scale misses are all un-tool-backed subtle-diff lanes**:
  [[interface-compat]] (type narrowing), [[data-contract]] (decimal scale cut),
  [[terraform]] (missed the IAM defect *only because checkov/trivy were absent*).
- False alarms cluster in the reasoning lanes; the tool-backed lanes were clean
  on both axes.
- Safety hooks are **conditional** (load only in a trusted, non-bypass session) —
  see [[safety-model]]. The unconditional guarantees come from the CLI + scratch
  branch.
- The lakehouse conventions are **private**, linked out, never copied here —
  see [[lakehouse]] and [[conventions-overlay]].

## Recent changes
- Created: this whole `vault/` (juror/lane/preset/research/eval/concept notes).
- Added earlier this session: orchestrator-brokered **interactivity** (Planner/
  Executor/Judge return questions, orchestrator asks via AskUserQuestion;
  `interactivity.level` default `high`).
- Added: the eval corpus (`examples/eval/`) — floor + adversarial + scale.

## Active threads
Audit (2026-06-28) reframed the priorities — biggest gaps, highest leverage first:
1. **Diff-router (Haiku triage)** — seat only the lanes the diff touches. Fixes
   *both* cost (don't spawn 38 of [[tool-backing|the jurors]] when 3 apply) and the
   "coverage = seating, done by hand" assumption. Top recommendation.
2. **Prompt caching** the shared prefix (contract + diff) across jurors — ~90% off
   the replicated input. Cheapest big win.
3. **Coverage check + Judge evidence spot-read** — the Judge is blind (ACCEPT =
   "no seated juror objected", not "correct"). See [[jje-loop]].
4. **Skipped-core = escalate, systemically** (done for 3 lanes via [[tool-backing]]).
5. **Prove the loop loops** — one real multi-iteration run (REVISE/REPLAN/ESCALATE)
   on a large PR; the loop has only ever run once, trivially. See [[scale-eval]].
6. Model right-sizing (31/38 on Sonnet vs config's haiku default); caveman ONLY on
   Judge/Planner/Executor prose, never jurors.
