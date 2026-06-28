#!/usr/bin/env bash
# SessionStart hook. Injects the Hot Cache (vault/hot.md) into the session as
# additional context, so every session — and every /jje run — starts with
# "where did we leave off?" without crawling the vault. No-ops if there is no
# hot cache. Keep the cache small (~500 words) so this stays cheap.
set -euo pipefail
PROJ="${CLAUDE_PROJECT_DIR:-$PWD}"
CFG="$PROJ/.jje/config.json"
if [ -f "$CFG" ] && [ "$(jq -r 'if .hot_cache == false then "false" else "true" end' "$CFG" 2>/dev/null)" = "false" ]; then
  exit 0
fi
HOT="$PROJ/vault/hot.md"
[ -f "$HOT" ] || exit 0
CONTENT="$(cat "$HOT")"
# Emit as SessionStart additionalContext (JSON), jq-escaped.
jq -cn --arg c "Project Hot Cache (vault/hot.md) — current state, read first:

$CONTENT" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
