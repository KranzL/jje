#!/usr/bin/env bash
# Lints the hook scripts. Uses shellcheck when present; always runs `bash -n`.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$REPO/.claude/hooks"
FAIL=0
for f in "$HOOKS"/*.sh "$REPO/scripts/package-plugin.sh"; do
  [ -f "$f" ] || continue
  if ! bash -n "$f"; then echo "  FAIL: bash -n $f"; FAIL=1; else echo "  ok: bash -n $(basename "$f")"; fi
  if command -v shellcheck >/dev/null 2>&1; then
    if ! shellcheck -S warning "$f"; then echo "  FAIL: shellcheck $f"; FAIL=1; else echo "  ok: shellcheck $(basename "$f")"; fi
  fi
done
command -v shellcheck >/dev/null 2>&1 || echo "  skip: shellcheck not installed"
exit "$FAIL"
