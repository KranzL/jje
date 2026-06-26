# Changelog

All notable changes to JJE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
semantic versioning (see CONTRIBUTING.md for what MAJOR/MINOR/PATCH mean here).

## [Unreleased]

### Added
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
