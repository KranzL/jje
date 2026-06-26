# Contributing to JJE

The roster is meant to be extended. A new lane is a new agent file plus a skill
file plus a config entry — **nothing else in the loop changes.** That property is
the whole point of the design; please preserve it.

## Add a new juror

Say you want a `licensing-juror` that flags GPL dependencies in a permissive repo.

### 1. The agent — `.claude/agents/jurors/licensing-juror.md`

Thin. Match `tools` to the lane and `model` to the cost (Haiku for tool-backed,
Sonnet for high-judgment). Preload the contract and your review skill.

```yaml
---
name: licensing-juror
description: JJE juror. Reviews dependency licenses only. Emits one verdict.
tools: Read, Grep, Glob, Bash
model: haiku
skills: [jje-contract, licensing-review]
---
Review the candidate for DEPENDENCY LICENSING only. Say nothing about other
lanes. Run the checks in skills/licensing-review/SKILL.md, cite evidence for
every finding, report skipped checks honestly, and emit exactly one verdict per
skills/jje-contract/SKILL.md. No prose outside the JSON.
```

The `name` field MUST exactly match the id you register in config (step 3), or
the orchestrator silently seats no one.

### 2. The skill — `.claude/skills/licensing-review/SKILL.md`

Where the domain knowledge lives, so the juror is editable in one place. Follow
the shape every review skill uses (see `security-review` as the reference):

1. **Scope to the change** — `BASE="${JJE_BASE:-HEAD~1}"`, `CHANGED=$(git diff
   --name-only "$BASE"...HEAD)`, detect the ecosystem from lockfiles.
2. **Run the checks** — gate every external tool on `command -v <tool>`; if
   absent, push to `skipped[]` and emit one advisory finding. Never infer what an
   un-run check would have found.
3. **Blocking bar** — state exactly what makes a finding `blocking: true`.
   Everything else is advisory. A finding with no evidence is advisory by rule.
4. **Emit the verdict** — one JSON object per `jje-contract`, written to
   `iterations/iter-<n>/verdicts/licensing-juror.json`, with stable
   `id = lic-<check>-<file>:<line>`.

Set `user-invocable: false` so it doesn't clutter the slash menu, but do NOT add
`disable-model-invocation: true` — that flag blocks the `skills:` preload the
juror depends on.

### 3. Register it — `.jje/config.json`

```json
"jurors": {
  "licensing-juror": {"agent": "licensing-juror", "skill": "licensing-review",
                      "lane": "code", "model": "haiku"}
},
"presets": {
  "code-full": ["...", "licensing-juror"]
}
```

Add the id to whatever presets should seat it, or define a new preset.

### 4. Document it

Add a row to the roster table in `README.md`.

### 5. Verify

```sh
tests/run-state-tests.sh        # the deterministic core still passes
tests/validate-config.sh        # your juror id resolves and presets reference real jurors
```

Then run JJE against `examples/sample-target/` with a preset that seats your
juror and confirm it produces a schema-valid verdict.

## Conventions

- No comments in code; no emojis. (Shell snippets inside skills are fine.)
- Keep agents thin and skills fat. If you find yourself putting commands in an
  agent file, they belong in the skill.
- The verdict contract is load-bearing. If you change `jje-contract`, bump the
  MAJOR version (see below) and update every juror and the schemas in `schema/`.
- Run `shellcheck` on any hook you touch.

## Versioning

Semver in `.claude-plugin/plugin.json`:

- **MAJOR** — a change to the verdict contract or the config schema.
- **MINOR** — a new juror, a new preset, or a new config field with a default.
- **PATCH** — fixes.

Record changes in `CHANGELOG.md`.
