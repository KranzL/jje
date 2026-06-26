#!/usr/bin/env bash
# Builds the plugin form of JJE from the canonical project-scoped .claude/ layout
# into dist/plugin/. This is the staged distribution path (see docs/PACKAGING.md);
# the project layout remains the tested canonical artifact.
#
# Transforms applied:
#   - flatten .claude/agents/ (incl. jurors/) into dist/plugin/agents/ so plugin
#     scoped names stay predictable (jje:<name>, not jje:jurors:<name>)
#   - move hooks into dist/plugin/hooks/hooks.json with ${CLAUDE_PLUGIN_ROOT} paths
#   - rewrite the orchestrator skill's script path to ${CLAUDE_PLUGIN_ROOT}
#   - copy skills, scripts, commands, and the plugin manifest
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/.claude"
OUT="$REPO/dist/plugin"

rm -rf "$OUT"
mkdir -p "$OUT/agents" "$OUT/skills" "$OUT/scripts" "$OUT/hooks" "$OUT/.claude-plugin"

# 1. Flatten agents.
find "$SRC/agents" -name '*.md' -exec cp {} "$OUT/agents/" \;
echo "flattened $(find "$OUT/agents" -name '*.md' | wc -l | tr -d ' ') agents"

# 2. Skills + scripts, then rewrite the orchestrator's script path.
cp -R "$SRC/skills/." "$OUT/skills/"
cp -R "$SRC/scripts/." "$OUT/scripts/"
if [ -f "$OUT/skills/jje/SKILL.md" ]; then
  sed -i.bak 's#\$CLAUDE_PROJECT_DIR/.claude/scripts/jje_state.py#${CLAUDE_PLUGIN_ROOT}/scripts/jje_state.py#g' \
    "$OUT/skills/jje/SKILL.md" && rm -f "$OUT/skills/jje/SKILL.md.bak"
fi

# 3. Hooks → hooks/hooks.json with plugin-root paths (plugin agent frontmatter
#    cannot carry hooks; the safety layer must live here).
cp "$SRC/hooks/"*.sh "$OUT/hooks/"
chmod +x "$OUT/hooks/"*.sh
cat > "$OUT/hooks/hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/jje-ci-gate.sh", "timeout": 10}
        ]
      },
      {
        "matcher": "Agent|Task",
        "hooks": [
          {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/jje-loop-guard.sh", "timeout": 10}
        ]
      }
    ]
  }
}
JSON

# 4. Manifest + optional commands.
cp "$REPO/.claude-plugin/plugin.json" "$OUT/.claude-plugin/plugin.json"
[ -d "$SRC/commands" ] && cp -R "$SRC/commands" "$OUT/commands" || true

echo "built plugin at $OUT"
echo "note: deny rules from .claude/settings.json are NOT bundled (plugins do not"
echo "carry permission rules); document that users keep those in their settings."
