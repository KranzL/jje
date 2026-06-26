#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Enforces the spec invariant: nothing reaches
# mainline until Judge ACCEPT + validated green CI.
#
# The Executor commits its candidate on a `jje/*` scratch branch during the loop,
# so those commits MUST be allowed. The gate keys on the branch the command
# actually targets — derived from a `-C <path>` in the command, else the tool's
# cwd, else the project root — not on the main checkout's branch (which was the
# original bug). A commit/merge that targets a protected branch requires the
# .jje/COMMIT_APPROVED marker (minted by `jje_state.py accept` after a validated
# green CI). The marker is single-use. Pushes to a protected upstream are always
# blocked.
set -euo pipefail

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || echo "")"
PROJ="${CLAUDE_PROJECT_DIR:-$PWD}"
MARKER="$PROJ/.jje/COMMIT_APPROVED"

deny() { printf '{"decision":"deny","reason":%s}\n' "$(jq -Rn --arg m "$1" '$m')"; exit 2; }

# Only police git mutations that can reach mainline.
case "$CMD" in
  *"git commit"*|*"git merge"*|*"git push"*) ;;
  *) exit 0 ;;
esac

PROTECTED="$(jq -r '(.protected_branches // ["main","master"]) | join(" ")' \
  "$PROJ/.jje/config.json" 2>/dev/null || echo "main master")"
[ -n "$PROTECTED" ] || PROTECTED="main master"
is_protected() { for b in $PROTECTED; do [ "$1" = "$b" ] && return 0; done; return 1; }

# Hard block: pushing to a protected upstream is never JJE's job.
if printf '%s' "$CMD" | grep -Eq 'git +push'; then
  for b in $PROTECTED; do
    if printf '%s' "$CMD" | grep -Eq "(origin[[:space:]/:]+)?$b\b"; then
      deny "JJE: direct push to protected branch '$b' is blocked. Open a PR from the scratch branch."
    fi
  done
  exit 0
fi

# Determine the directory the git command actually operates in: an explicit
# `-C <path>` wins, else the tool's cwd, else the project root.
DIR="${CWD:-$PROJ}"
GITC="$(printf '%s' "$CMD" | grep -oE '(^|[[:space:]])-C[[:space:]=]+[^[:space:]]+' | head -1 | sed -E 's/.*-C[[:space:]=]+//' || true)"
if [ -n "$GITC" ]; then
  case "$GITC" in /*) DIR="$GITC" ;; *) DIR="${CWD:-$PROJ}/$GITC" ;; esac
fi
BRANCH="$(git -C "$DIR" symbolic-ref --short HEAD 2>/dev/null || echo unknown)"

# Commits on a JJE scratch branch are the candidate; always allowed.
case "$BRANCH" in
  jje/*) exit 0 ;;
esac

# A commit/merge that targets a protected (or undeterminable) branch while a run
# is active requires the approval marker.
if is_protected "$BRANCH" || [ "$BRANCH" = "unknown" ] || printf '%s' "$CMD" | grep -Eq 'git +merge'; then
  if [ -f "$PROJ/.jje/ACTIVE" ]; then
    if [ ! -f "$MARKER" ]; then
      deny "JJE: a run is active and this commit/merge targets '$BRANCH' without Judge ACCEPT + green-CI approval (no .jje/COMMIT_APPROVED). Let the loop run \`accept\` first."
    fi
    rm -f "$MARKER"   # single-use: consume so it cannot authorize a later commit
  fi
fi
exit 0
