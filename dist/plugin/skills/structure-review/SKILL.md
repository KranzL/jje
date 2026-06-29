---
name: structure-review
description: The structure juror's checklist and exact commands for naming, module boundaries, and agreed conventions.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

# structure review
You review ONLY structure: naming, module/package boundaries, import layering, agreed architectural standards. Stay in lane.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Review only $CHANGED. Detect ecosystem from lockfiles (go.mod, package.json, pyproject/requirements, Cargo.toml, dbt_project.yml).

## 2. Context to load
Read where present: the architecture/layer doc (intended dependency direction between packages); layer-enforcement config (`eslint import/no-restricted-paths` rules, CODEOWNERS groupings as module-boundary proxy); convention files (CONTRIBUTING, STYLE, CLAUDE.md). Without a layer doc a layering violation is advisory, not blocking.

## 3. Reference conventions (anchor all findings here, never to taste)
- **Python** — PEP 8: `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` module-level constants.
- **Go** — Effective Go (go.dev/doc/effective_go): `PascalCase` exported identifiers, `camelCase` unexported, short lowercase package names, no stutter (`package foo; type Reader`, never `FooReader`).
- **ADP** — Martin, *Agile Software Development: Principles, Patterns, and Practices* (2002): no cyclic dependencies between packages; a cycle is always a structural defect, never a style preference.
- **SRP** — SOLID (Martin, 2002): a module with multiple independent reasons to change must be split.

## 4. Run the checks (gate every external tool on `command -v`; absent → skipped[] + one info finding; never infer)
**Cycle detection — always run first:**
- Go: `go build ./...` (native; "import cycle not allowed" = compile error).
- JS/TS: `madge --circular .` if installed.
- Python: `pylint --disable=all --enable=cyclic-import $CHANGED` if installed.

**Naming:**
- `grep -nE '\b(temp|data|util|helper|manager|processor)[0-9]*\b' $CHANGED` — stale generic names.
- Flag mixed naming styles within one file (camelCase alongside `snake_case` in a Python file; underscore in a Go exported identifier).

**Layering:**
- Trace every new import in $CHANGED; flag any import where a lower-abstraction package pulls in a higher one (`core` → `ui`, `domain` → `infra`, `models` → `controllers`).
- Flag cross-module reach-through: a package importing a deep internal subpackage instead of the published API.

**Lint (structural findings only):** `ruff check --select=N $CHANGED --no-fix` (Python); `cargo clippy --no-deps` (Rust).

## 5. Blocking bar
Set blocking:true (cite file:line, the offending import, and the authority) ONLY for:
- **Import cycle between packages** — confirmed by `go build ./...` output or `madge --circular` output. ADP violation; always blocking regardless of intent.
- **Import crossing the stated layer contract** — the architecture doc names the forbidden direction AND the diff introduces an import crossing it; cite the doc section and the offending import line.
Everything else is advisory: God-file size, wrong file placement, naming violations, mixed style, stutter, catch-all packages. A finding with no evidence is advisory by rule.

## 6. Anti-patterns to hunt
- Import cycle between packages (ADP; silent defect in Python/JS, compile failure in Go).
- Layer inversion: lower-abstraction layer importing higher (`domain` → `presentation`, `core` → `adapters`).
- Cross-module reach-through: importing a deep internal subpackage instead of the module's public API.
- God file: a single module with multiple unrelated responsibilities and no cohesive abstraction.
- Catch-all packages: `util`, `helper`, `common`, `misc` with no cohesive abstraction — a boundary was never defined.
- Barrel-export explosion: `index.ts`/`__init__.py` re-exporting every submodule symbol, making the public surface unbounded.
- Mixed naming conventions in one file: camelCase identifiers alongside `snake_case` in Python; underscore in a Go exported identifier.
- Package stutter: `foo.FooReader`, `auth.AuthService` — Effective Go explicitly prohibits.

## 7. Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/structure-juror.json. ran[]/skipped[] honest. id = struct-<check>-<file>:<line>. Nothing outside the JSON.
