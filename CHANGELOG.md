# Changelog

All notable changes to JJE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
semantic versioning (see CONTRIBUTING.md for what MAJOR/MINOR/PATCH mean here).

## [Unreleased]

### Added (20 principal-level data jurors — roster now 38)
- **Data-modeling lane**: `dimensional-modeling`, `slowly-changing-dimensions`,
  `normalization-relational`, `semantic-layer-metrics` (preset `data-modeling`).
- **Machine-learning lane**: `data-leakage`, `feature-engineering`,
  `model-evaluation`, `ml-reproducibility`, `model-serving-mlops`,
  `model-monitoring-drift` (preset `ml`).
- **Data-science lane**: `statistical-rigor`, `experimentation-abtest`,
  `causal-inference`, `notebook-productionization` (preset `data-science`).
- **Data-platforms lane**: `streaming-eventtime`, `orchestration-dag`,
  `query-performance-sql`, `distributed-compute-spark` (preset `data-platforms`).
- **DS&algorithms lane**: `algorithmic-complexity`, `data-structure-selection`
  (preset `dsa`).
- All 20 are Sonnet judgment lanes researched to principal depth (Kimball,
  Kohavi/trustworthy-experiments, Akidau, the MLOps/stats/causal canon); each
  review skill is an enforceable checklist with a principal-level blocking bar.
  Opt-in via the new presets; `quick`/`code-full` are unchanged.

### Fixed (from the first real end-to-end run)
- **zsh-breaking state helper.** The skill defined `S="python3 …"` then `$S init`,
  which fails on zsh (the macOS default) because zsh does not word-split unquoted
  expansions — the very first command exited 127. Replaced with a shell function
  `S(){ … }` that works in both shells.
- **Gitignored files in scope silently evaporate.** A plan that scoped a gitignored
  file (`CLAUDE.md`) had that work written to a worktree copy that could never be
  committed or appear in any diff/verdict. Planner now `git check-ignore`s every
  `files_in_scope` entry (drops/flags ignored ones); Executor refuses to edit a
  gitignored file and records it in `blocked`.
- **The Judge's "fast follow-up" was a phantom.** ACCEPT is terminal (CI → merge →
  close ends the run), so a clarification offering "accept now, fix as a follow-up"
  promised work that never happens. The Judge now frames advisories as fold-in-now
  (REVISE) vs ship-as-is (ACCEPT).
- **Marker lifecycle on the PR path.** The skill assumed a local merge consumes the
  `COMMIT_APPROVED` marker; on the PR path there is no local protected-branch commit
  so it isn't consumed. Documented that `close` clears any unconsumed marker (it
  already did) so a stray future local commit can't be authorized.

### Added (human-in-the-loop interactivity)
- The loop now pulls the user in at the plan/execute/judge stages via
  `AskUserQuestion`, brokered by the orchestrator (the Planner/Executor/Judge are
  subagents and can't prompt; they return `questions_for_user` /
  `decisions_needed` / `clarifications` and the orchestrator asks the user, then
  feeds answers back). New `interactivity.level` config (`minimal`/`normal`/
  `high`/`max`, default `high`) with `max_questions_per_turn`. `minimal` keeps
  unattended/CI runs autonomous.

### Added (project conventions overlay)
- Jurors can now review against **project-specific conventions**: drop
  `### <lane>`-organized rules in `.jje/conventions/*.md` (gitignored, local) and
  the orchestrator passes each juror the section matching its domain, with
  `(blocking)` rules becoming additional blocking bars. The mechanism is generic
  and public; the conventions content stays local. See `.jje/conventions.example.md`.

### Added (research-driven: stronger agents, IaC, deployment)
- **IaC lane**: `terraform-juror` (AWS Terraform — Checkov/Trivy/tflint/Infracost,
  security + IAM + encryption + state hygiene + cost), plus an `iac` preset.
  Note: uses Trivy (`tfsec` is deprecated) and Checkov (Terrascan is archived).
- **Deploy lane**: `deployment-juror` (Kargo + Argo CD/Rollouts GitOps promotion
  safety — verification gates, stage-skip, unpinned Freight, human gates,
  rollback), plus a `deploy` preset. Built from research verified against the
  official Kargo docs.
- **Eval corpus** (`examples/eval/`): seeded-defect fixtures + a case manifest +
  a CI-able structural validator (`tests/validate-eval.sh`) and an opt-in recall
  grader (`tests/run-eval.sh`) to measure per-lane juror false-negative rate.

### Changed (agent-strengthening, from the 2026 multi-agent-judge research)
- Jurors now treat the Executor's self-report as **advisory only** and may not set
  or clear `blocking` from it; a finding clears only on a re-run with fresh
  evidence (counters anchoring/sycophancy + the self-correction illusion). Added
  anti-pattern-hunting guidance to the verdict contract.
- **`security-juror` moved to Sonnet** (from Haiku) — small models miss
  injection/authz/secret blockers, the most expensive juror error.

### Changed
- Reframed as a **harness** (not a single skill) across the README, plugin
  manifest, and docs, with an explicit two-tier safety model.

### Fixed (driven by a gap-hardening test pass — see docs/TEST-FINDINGS.md)
- `check-guards` now **fails safe** on a malformed or schema-invalid verdict
  (treats it as a blocking finding) instead of crashing on bad JSON or silently
  dropping a finding that lacks the `blocking` key (T3.1).
- The commit gate now **binds the approval marker to the CI-validated sha** — a
  candidate that changed after CI can no longer merge on a stale approval (T3.2).
- `close` now garbage-collects the run's worktree and scratch branch (T4.1).
- Documented the **conditional nature of the hooks**: they enforce only in a
  trusted workspace and a non-bypass permission mode; the unconditional
  guarantees come from the deterministic CLI + orchestrator discipline (Bucket 1).
- Planner and all jurors carry a `Write` tool so they can emit their own output
  files (two jurors previously had no write path).

### Added
- **Go lane** jurors: `go-concurrency` (data races / goroutine leaks via
  `go test -race`), `go-error-handling` (errcheck / wrapping / panic),
  `go-performance` (allocations / escape analysis / benchmarks), plus a `go` preset.
- **Datalake lane** jurors: `table-format` (Iceberg/Delta/Hudi schema + ACID),
  `partitioning-layout` (small files / compaction / clustering), `storage-format`
  (Parquet/ORC/Avro / compression / pushdown), plus a `datalake` preset.
- Initial JJE harness: Planner / Executor / Jury / Judge generator–critic loop
  on portable Claude Code primitives.
- `jje` orchestration skill driving the loop from the main agent.
- 10 jurors across the code and data-pipeline lanes, each a thin agent plus a
  self-contained review skill (`<lane>-review`).
- `jje-contract` skill: the verdict JSON shape, preloaded into every juror.
- `jje_state.py` deterministic core: authoritative iteration counter, oscillation
  ledger with a line-tolerant finding fingerprint, verifiable CI result artifact,
  single-use commit marker, and a run lock.
- Two PreToolUse hooks: `jje-loop-guard.sh` (model-independent budget +
  oscillation backstop) and `jje-ci-gate.sh` (commit gate; nothing reaches a
  protected branch without ACCEPT + validated green CI).
- Jury seating via presets (`quick`, `code-full`, `pipeline`, `security-sweep`,
  `full`, `custom`).
- `examples/sample-target/` fixture (planted SQL injection + failing test) and a
  golden-run expectation set.
- Deterministic test suite (`tests/`) and GitHub Actions CI.
- Staged plugin/marketplace packaging (`.claude-plugin/`, `docs/PACKAGING.md`).
