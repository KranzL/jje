---
name: go-modules-review
description: The go-modules juror's checklist and exact commands for go.mod/go.sum hygiene, replace directive safety, vendoring consistency, embed glob safety, and major-version import path alignment.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---
# go modules review
You review ONLY Go module-graph integrity: go.mod/go.sum hygiene, replace directive safety, vendoring consistency, //go:embed glob safety, major-version import path alignment, and toolchain pinning. Stay in lane: CVE scanning belongs to security; allocation hot paths to go-performance; concurrency to go-concurrency; error semantics to go-error-handling.

## 1. Scope to the change
```sh
BASE="${JJE_BASE:-HEAD~1}"
CHANGED="$(git diff --name-only "$BASE"...HEAD)"
```
Detect Go modules: look for go.mod in CHANGED or in the repo root. If no go.mod is present and no .go files changed, emit empty findings[] and stop.

## 2. Run the checks (gate every external tool on `command -v`; absent -> skipped[] + one info finding)
- **Tidy drift**: `command -v go` required. Run `go mod tidy -diff` (Go 1.23+, no-write diff); fall back on older toolchains to `go mod tidy && git diff --exit-code go.mod go.sum`, then restore with `git checkout go.mod go.sum`. Any delta is blocking.
- **Verify**: run `go mod verify`. Any module whose content hash does not match its go.sum entry is blocking; this is supply-chain integrity, not CVE scanning.
- **Replace directives**: grep go.mod for `^replace`. Flag relative-path (`../`) or absolute-path pins as blocking when the module carries a release tag or is required by another internal module. Flag remote-ref replaces that shadow a dependency older than the version being replaced as advisory.
- **Vendor consistency**: if vendor/ is committed, run `go mod vendor` then `git diff --exit-code vendor/` and restore with `git checkout -- vendor/` regardless of outcome. Any delta is blocking when `-mod=vendor` is enforced in CI (grep `GOFLAGS`, Makefile, CI YAML for `-mod=vendor`).
- **Embed glob safety**: grep changed .go files for `//go:embed`. Flag `//go:embed *` or `//go:embed .` as advisory (unrestricted tree includes).
- **Major-version alignment**: parse the go.mod `module` line for a `/vN` suffix. Grep changed .go files for imports of the same base module path without the correct suffix (or with the wrong suffix). Block on mismatch. Require a `toolchain` directive when the go.mod `go` line is 1.21 or higher; flag its absence as advisory.

## Blocking bar
Set `blocking: true` (cite file:line as evidence) ONLY for:
- `go mod tidy -diff` or `go mod tidy && git diff --exit-code` produces a non-empty diff on go.mod or go.sum.
- `go mod verify` reports a hash mismatch on any module.
- A `replace` directive using a relative or absolute local path in a module that carries a semver release tag or is required by another internal module.
- `go mod vendor && git diff --exit-code vendor/` produces a non-empty diff when `-mod=vendor` is active in CI.
- go.mod `module` path major-version suffix does not match the import paths used in changed .go files.
Everything else is advisory: missing `toolchain` directive; remote-ref replace shadowing an older version; vendor drift when `-mod=vendor` is not CI-enforced; `//go:embed *` or `//go:embed .` unrestricted globs. A finding with no evidence is advisory by rule.

## Anti-patterns to hunt
- `replace` directives with `../` or absolute paths in a module that carries a semver tag.
- go.sum entry absent for a module listed in go.mod (uncommitted tidy drift without running the check).
- Vendor directory committed but stale: `vendor/modules.txt` predates the most recent go.mod change.
- `//go:embed *` or `//go:embed .` (unrestricted embed grabs all files under the directory).
- go.mod `go 1.21` or higher with no `toolchain` line (non-reproducible toolchain selection across environments).
- Module path missing `/v2` suffix when the repo carries a v2+ semver tag and internal imports reference the versioned path.
- Hand-edited files in vendor/ diverging from upstream source (grep for `// Modified` markers, or a `vendor/modules.txt` out of sync with go.mod).

## Emit the verdict
One JSON object per skills/jje-contract/SKILL.md, written to iterations/iter-<n>/verdicts/go-modules-juror.json. ran[]/skipped[] honest. id = gomod-<check>-<file>:<line>. Nothing outside the JSON.
