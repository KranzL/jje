# Changelog

All notable changes to JJE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
semantic versioning (see CONTRIBUTING.md for what MAJOR/MINOR/PATCH mean here).

## [Unreleased]

### Added (Go + datalake lane expansion — roster now 47)
- **9 new jurors** filling coverage gaps a real Go/lakehouse review needs, surfaced by
  an adversarial completeness audit of both lanes:
  - **Go**: `go-http-safety` (server/client timeouts, body limits, DefaultClient),
    `go-modules` (go.mod/go.sum integrity, replace/vendor/embed, v2 paths — backed by
    `go mod verify`/`tidy`), `go-db-sql` (Rows/tx lifecycle — `sqlclosecheck`/`rowserrcheck`),
    `go-time` (time.Time equality, zone-aware parsing, UTC storage), `go-serialization`
    (json tag drift, >2^53 precision, MarshalJSON receiver dispatch).
  - **Datalake**: `merge-upsert` (MERGE/UPDATE/DELETE DML correctness), `cdc-ingest`
    (source-order/dedup/tombstones), `catalog-metastore-ops` (partition registration,
    catalog drift), `multi-engine-interop` (protocol/feature-flag vs declared engines).
- Each was drafted from a vetted spec, then put through draft → adversarial fact-check →
  correct-or-remove convergence; the checks caught invented linter flags, wrong spec
  versions, and inverted facts (e.g. `MarshalJSON` receiver, `log(0)`→NaN) before shipping.
- Add-checks to existing jurors: comparable-generics panic (`go-error-handling`),
  orphan-file + checkpoint-vs-snapshot-expiration (`table-format`), backfill-overlap
  (`idempotency`), unscheduled-maintenance (`partitioning-layout`).
- The `router` seats them on the right signals; the `go`/`datalake`/`everything` presets
  are extended. The Go tool-backing was verified live (`go test -race`, `go vet`,
  escape analysis, `errcheck`, `golangci-lint` all fired on planted defects).

### Fixed (from a real field run on an external repo)
- **`CLAUDE_PROJECT_DIR` self-establishes.** The skill derives and exports it from the
  git root if unset, so the first `S` call no longer fails in a plain shell.
- **`base_ref` is pinned to a SHA at init** (was the literal `HEAD`), so a re-run that
  adds commits still lets jurors diff against the original baseline.
- **A contradiction no longer traps the run forever.** `check-guards` auto-resolves a
  recorded contradiction once neither side still blocks (plus a `resolve-contradiction`
  command), so a later clean candidate can reach ACCEPT — previously any recorded
  contradiction forced `recommend_escalate` permanently.
- **The Judge reads the real verdict files.** It is now passed absolute verdict paths
  and must read exactly those (flagging unreadable ones as a blocking unknown) instead
  of routing off the prompt summary when its working dir pointed at a stale run.
- **A committed build artifact is caught.** `check-guards` runs a deterministic hygiene
  scan and reports any added file > 5 MB; the orchestrator treats it as blocking (a
  71 MB binary previously slipped through to push).
- **Morphing recurrences get a soft signal.** `check-guards` reports `persistent_jurors`
  (a juror blocking across ≥3 iterations even if the finding text changes), which the
  Judge weighs as recurrence-grade thrash — the literal fingerprint guard alone missed
  a finding that changed shape.

### Changed (juror strengthening — all 38 review skills to industry-standard depth)
- Every juror review skill was audited against the `data-leakage` gold standard, then
  strengthened to principal depth: named authoritative canon with real numbers (e.g.
  `storage-format` now cites Parquet `block.size` 128MB / ORC stripe 64MB / ZSTD RFC
  8478; `security` cites OWASP Top 10 2021 / CWE Top 25 / ASVS 4.0 with CVSS bands;
  `governance` cites GDPR Art. 4(1)/9, HIPAA §164.514(b), PCI-DSS v4.0 Req 3), concrete
  quantified checks with grep tells, an `Anti-patterns to hunt` section, and a crisp
  gating-vs-advisory blocking bar. Skills are now a uniform 47–74 lines (was 24–86).
- The strengthening was hardened by **three adversarial fact-check rounds** (each cited
  standard independently verified, hallucinated specifics removed under a correct-or-
  remove rule) plus manual fixes — e.g. corrected Avro BACKWARD/FORWARD direction,
  golangci-lint `goerr113`→`err113`, checkov `--check-severity`→`--severity`, and the
  IEEE-754 `log(0)` (−Inf, not NaN) case. No unverified standard ships.

### Changed (seating redesign — tiers + an auto-router)
- Seating is now by **tier** (`quick` / `auto` (default) / `full` / `custom`), not by
  hand-picking a lane preset. A new Haiku **`router`** agent reads the finalized plan
  and seats the correctness+security **core** plus only the lanes the change actually
  touches; the user can always edit its picks (a genuine multi-select, with a free-text
  add/drop escape so the AskUserQuestion 4-option cap never silently truncates). New
  `default_tier` config key (default `auto`). The per-lane presets are retired from the
  seating UX and kept only as the router's lane knowledge and `custom` shorthand; the
  all-roster preset is renamed `everything` to avoid clashing with tier `full`.

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
