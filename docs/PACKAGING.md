# Packaging & distribution

JJE ships in two forms. The **project-scoped `.claude/` layout** is the canonical,
tested artifact. The **plugin/marketplace** form is a borrowable convenience built
from the same payload. This document is the plan for the plugin form — it is
staged (manifests + a transform script exist) but the project layout is what's
validated in CI.

## Form 1 — project-scoped (canonical)

What this repo is. Copy `.claude/` and `.jje/` into a target repo, copy
`config.example.json` to `config.json`, run `/jje`. Clean `/jje` invocation, no
namespacing, `${CLAUDE_PROJECT_DIR}` paths in hooks. This is what the tests and
the golden run exercise. Recommend it as the primary path until the plugin form
has equivalent test coverage.

## Form 2 — Claude Code plugin + marketplace (staged)

A single GitHub repo that is simultaneously a plugin and its own one-entry
marketplace. A borrower runs:

```
/plugin marketplace add KranzL/jje
/plugin install jje@jje
```

This buys versioned distribution and background auto-updates keyed to
`plugin.json` version, so borrowers track releases instead of copy-pasting.

### What changes from the project layout

Plugins are copied to a cache, and plugin component identity differs from
project scope. The transform (`scripts/package-plugin.sh`) handles:

1. **Flatten `agents/`.** A plugin folds an agent's subdirectory into its scoped
   name, so `agents/jurors/security-juror.md` would become
   `jje:jurors:security-juror`. Flatten all 13 agents into one `agents/`
   directory so names stay predictable (`jje:security-juror`).
2. **Hooks move to `hooks/hooks.json`** at the plugin root, with commands
   referenced via `${CLAUDE_PLUGIN_ROOT}` (not `${CLAUDE_PROJECT_DIR}` — the
   scripts ship inside the cached plugin). Plugin subagent frontmatter ignores
   `hooks`/`mcpServers`/`permissionMode`, so the safety layer MUST live here.
3. **Script paths** resolve via `${CLAUDE_PLUGIN_ROOT}/scripts/jje_state.py` with
   a `${CLAUDE_PROJECT_DIR}` fallback. The run state and markers still live under
   the user's repo (`${CLAUDE_PROJECT_DIR}/.jje/`).
4. **Invocation becomes namespaced**: the orchestrator skill is `/jje:jje`.
   Crucially, the orchestrator invokes jurors by their `name` frontmatter via
   natural-language delegation ("spawn the security-juror subagent") — the same
   string in both forms — never by slash/@-name, which differs. That keeps both
   install paths working from one set of agent prose.

### Why not split into multiple plugins

`jje-core` + `jje-code-jury` + `jje-data-jury` as separate marketplace entries is
cleaner separation and lets users install only the lanes they need, but it adds
cross-plugin version coordination and the orchestrator must resolve jurors across
plugin boundaries. Defer to v2 once the roster is large.

## Quality gates

- `tests/lint-hooks.sh` — `shellcheck` on the hook scripts.
- `tests/validate-schemas.sh` — the JSON Schemas parse and the example verdict
  validates against the verdict schema.
- `tests/validate-config.sh` — `config.example.json` parses, every preset
  references a registered juror, every juror names an agent + skill that exist.
- `tests/run-state-tests.sh` — the deterministic core: budget refusal, the
  oscillation fingerprint catching a re-flagged finding, `accept` refusing
  without a green CI artifact.
- The live-LLM golden run against `examples/sample-target/` is opt-in (gated
  behind an API key) so forks pass CI without one.

## License

Apache-2.0 — chosen over MIT for the explicit patent grant, which organizations
adopting internal tooling tend to prefer.
