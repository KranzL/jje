# Changelog

All notable changes to JJE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
semantic versioning (see CONTRIBUTING.md for what MAJOR/MINOR/PATCH mean here).

## [Unreleased]

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
