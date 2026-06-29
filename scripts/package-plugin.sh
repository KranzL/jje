#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist/plugin"
VERSION="${1:-$(python3 -c "import json;print(json.load(open('$ROOT/.claude-plugin/plugin.json'))['version'])")}"

rm -rf "$OUT"
mkdir -p "$OUT/.claude-plugin" "$OUT/skills" "$OUT/agents" "$OUT/hooks"

cp -R "$ROOT/.claude/skills/." "$OUT/skills/"
mkdir -p "$OUT/skills/jje/scripts"
cp "$ROOT/.claude/scripts/jje_state.py" "$OUT/skills/jje/scripts/jje_state.py"
cp "$ROOT/.jje/config.example.json" "$OUT/skills/jje/config.example.json"

cp "$ROOT/.claude/agents/"*.md "$OUT/agents/"
cp "$ROOT/.claude/agents/jurors/"*.md "$OUT/agents/"

cp "$ROOT/.claude/hooks/"*.sh "$OUT/hooks/"
chmod +x "$OUT/hooks/"*.sh
cat > "$OUT/hooks/hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/jje-ci-gate.sh", "timeout": 10 } ] },
      { "matcher": "Agent|Task", "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/jje-loop-guard.sh", "timeout": 10 } ] }
    ],
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/jje-hot-cache.sh", "timeout": 10 } ] }
    ]
  }
}
JSON

python3 - "$OUT/.claude-plugin/plugin.json" "$VERSION" <<'PY'
import json, sys
out, version = sys.argv[1], sys.argv[2]
json.dump({
  "name": "jje",
  "version": version,
  "description": "Judge, Jury, Executioner — a generator-critic review harness. NOTE: plugin form is EXPERIMENTAL, not yet live-verified; the project-scoped cp -r install is the tested form (see README).",
  "author": {"name": "KranzL"},
  "license": "Apache-2.0",
  "keywords": ["code-review", "agents", "jury", "generator-critic", "ci-gate"],
  "homepage": "https://github.com/KranzL/jje"
}, open(out, "w"), indent=2)
PY

echo "built $OUT (version $VERSION)"
echo "  skills: $(ls "$OUT/skills" | wc -l | tr -d ' ') | agents: $(ls "$OUT/agents"/*.md | wc -l | tr -d ' ') | hooks: $(ls "$OUT/hooks"/*.sh | wc -l | tr -d ' ')"
echo "  jje_state.py in skill dir: $([ -f "$OUT/skills/jje/scripts/jje_state.py" ] && echo yes || echo NO) | roster shipped: $([ -f "$OUT/skills/jje/config.example.json" ] && echo yes || echo NO)"
echo "note: deny rules from .claude/settings.json are NOT bundled (plugins carry no permission rules); document that users keep those in their own settings."
