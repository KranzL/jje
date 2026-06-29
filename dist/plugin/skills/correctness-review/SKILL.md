---
name: correctness-review
description: The correctness juror's checklist and exact commands — run the test suite by ecosystem, reason about edge cases — and the bar for a blocking finding.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# Correctness review

You review ONLY logic, edge cases, and algorithmic correctness. Stay in lane: performance profiling belongs to performance-review; lint/style to structure-review.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect the ecosystem: `go.mod` → Go, `package.json` → JS/TS, `pyproject.toml`/`requirements.txt` → Python, `Cargo.toml` → Rust.

## 2. Static analysis (gate each on `command -v`; absent → skipped[] + one info finding)

| Ecosystem | Command |
|---|---|
| Go | `go vet ./...` (ships with toolchain); `staticcheck ./...` if installed |
| Python | `mypy --strict <changed .py files>` |
| Rust | `cargo clippy -- -D warnings` |

These catch printf-format mismatches, wrong-type arguments, unreachable code, and lock-copied-by-value before tests run.

## 3. Run the tests (gate each on the tool being present)

| Ecosystem | Command |
|---|---|
| Python | `pytest -q` |
| Go | `go test ./...`; add `-race` for any changed code touching goroutines or shared state |
| Rust | `cargo test` |
| JS/TS | `npm test --silent` / `pnpm test` / `yarn test` (whichever lockfile is present) |

Capture failing test node ids verbatim — they are your evidence and must be stable across iterations.

## 4. Reason where tools can't reach
The `success_criteria` in `plan.json` are the spec. Beyond pass/fail, check:
- **IEEE 754-2019 float equality**: flag `==` where either operand is a computed float/double (not a literal). NaN != NaN always; `0.0/0.0`, `sqrt` of negative, or `log(-1)` produce NaN that silently corrupt conditionals and aggregations. No epsilon/ULP/`isnan`/`isfinite` guard is a defect.
- **Integer silent wrap**: Go wraps silently on overflow for fixed-width types; Rust panics in debug but wraps silently in `--release`; JS bitwise ops truncate to 32-bit signed int; Python arbitrary-precision is exempt.
- **Error swallowing**: grep `_ = err` (Go), bare `except[:\s]` or `except Exception:\s*pass` (Python), `.unwrap()` outside `#[cfg(test)]` (Rust), unhandled Promise rejections (JS/TS).
- **Concurrency**: unsynchronized map write, read-modify-write without a lock, channel direction errors. `go test -race` is the only reliable confirmation in Go.
- **Off-by-one and boundary**: zero, empty, max index, unicode codepoint boundaries, signed/unsigned edge.

## 5. Anti-patterns to hunt
- Python bare `except:` or `except Exception: pass` — error swallowed, incorrect state propagates silently.
- Go `_ = err` or missing `if !ok` on map lookup or type assertion — silent failure.
- Rust `.unwrap()` / `.expect()` outside `#[cfg(test)]` on any user-reachable or high-frequency path.
- `==` on a computed float/double with no epsilon or `isnan`/`isfinite` guard (IEEE 754-2019 NaN semantics).
- Shallow-copy aliasing: mutable collection passed by reference then mutated, producing caller-visible side effects.
- Integer arithmetic on user-controlled input without bounds check in Go or Rust `--release` mode.

## 6. Blocking bar
Set `blocking: true` (cite file:line and evidence) ONLY for:
1. A failing test node id caused by this change.
2. Wrong output against a `success_criteria` item with a reproducing input.
3. IEEE 754 `==` on a computed float/double with no epsilon/ULP/`isnan`/`isfinite` guard, or NaN/Inf flowing into a branch or aggregation return.
4. A data race confirmed by `go test -race` or thread-sanitizer output.
5. A swallowed error (`_ = err`, bare `except:`, unhandled rejection) on a non-trivial path representing a real failure mode.

Everything else is advisory: theoretical edge cases without a reproducing input, complexity below the threshold, integer wrap on internal-only arithmetic, missing coverage, style.

## 7. Emit the verdict
One JSON object per `skills/jje-contract/SKILL.md`, written to
`iterations/iter-<n>/verdicts/correctness-juror.json`. `id` =
`corr-<check>-<file>:<line>` (use the test node id as `<check>` for test
failures). `ran[]`/`skipped[]` honest. Nothing outside the JSON.
