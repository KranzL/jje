#!/usr/bin/env bash
# Integration test for the two PreToolUse hooks against a REAL git repo with a
# scratch-branch worktree. Asserts the deny/allow exit codes for the payloads
# Claude Code feeds the hooks. Requires jq + git.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$REPO/.claude/scripts/jje_state.py"
CIGATE="$REPO/.claude/hooks/jje-ci-gate.sh"
GUARD="$REPO/.claude/hooks/jje-loop-guard.sh"
PASS=0; FAIL=0
ok() { echo "  ok: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1 (exit $2)"; FAIL=$((FAIL+1)); }
command -v jq >/dev/null || { echo "jq required"; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PROJECT_DIR="$TMP"
field() { python3 -c "import json,sys;print(json.loads(sys.stdin.read())[sys.argv[1]])" "$1"; }

# Real git repo on main, one base commit, plus a jje/ scratch worktree.
git -C "$TMP" init -q
git -C "$TMP" config user.email t@t.t; git -C "$TMP" config user.name t
echo base > "$TMP/f.txt"; git -C "$TMP" add -A; git -C "$TMP" commit -qm base
WT="$TMP/.jje/worktrees/wt"; mkdir -p "$TMP/.jje/worktrees"
git -C "$TMP" worktree add -q -b jje/test "$WT" HEAD

OUT="$(python3 "$STATE" init --request hooktest --budget 2 --force)"
RUN="$(printf '%s' "$OUT" | field run_dir)"

# run a hook with command + cwd; echo exit code
hook() { printf '{"cwd":%s,"tool_input":{"command":%s}}' \
  "$(jq -Rn --arg c "$3" '$c')" "$(jq -Rn --arg c "$2" '$c')" | "$1"; }
spawn() { printf '{"tool_input":{"subagent_type":%s}}' "$(jq -Rn --arg s "$2" '$s')" | "$1"; }

echo "== ci-gate: scratch-branch commit is the candidate =="
hook "$CIGATE" "git -C $WT commit -m candidate" "$TMP"; rc=$?
[ "$rc" -eq 0 ] && ok "commit on jje/* scratch branch allowed during active run" || bad "scratch commit should be allowed" "$rc"

echo "== ci-gate: protected-branch commit needs the marker =="
hook "$CIGATE" "git commit -m onmain" "$TMP"; rc=$?
[ "$rc" -eq 2 ] && ok "commit on main denied without marker" || bad "main commit should be denied" "$rc"
hook "$CIGATE" "ls -la" "$TMP"; rc=$?
[ "$rc" -eq 0 ] && ok "non-git command allowed" || bad "non-git should pass" "$rc"
hook "$CIGATE" "git push origin main" "$TMP"; rc=$?
[ "$rc" -eq 2 ] && ok "push to main denied" || bad "push to main should be denied" "$rc"

echo "== ci-gate: marker authorizes one protected commit =="
printf '{}' > "$TMP/.jje/COMMIT_APPROVED"
hook "$CIGATE" "git commit -m approved" "$TMP"; rc=$?
[ "$rc" -eq 0 ] && ok "main commit allowed with marker" || bad "main commit should be allowed" "$rc"
[ ! -f "$TMP/.jje/COMMIT_APPROVED" ] && ok "marker consumed (single-use)" || bad "marker should be consumed" 0
hook "$CIGATE" "git commit -m replay" "$TMP"; rc=$?
[ "$rc" -eq 2 ] && ok "second main commit denied (no replay)" || bad "replay should be denied" "$rc"

echo "== loop-guard: model-independent spawn cap (budget 2) =="
spawn "$GUARD" planner; rc=$?
[ "$rc" -eq 0 ] && ok "planner spawn ignored by guard" || bad "planner should pass" "$rc"
spawn "$GUARD" executor; rc=$?; [ "$rc" -eq 0 ] && ok "executor spawn 1 allowed" || bad "exec 1" "$rc"
spawn "$GUARD" executor; rc=$?; [ "$rc" -eq 0 ] && ok "executor spawn 2 allowed" || bad "exec 2" "$rc"
spawn "$GUARD" executor; rc=$?
[ "$rc" -eq 2 ] && ok "executor spawn 3 denied (hard cap, no start-iteration called)" || bad "exec 3 should be capped" "$rc"

echo "== ci-gate: no active run =="
python3 "$STATE" close --run "$RUN" >/dev/null
hook "$CIGATE" "git commit -m free" "$TMP"; rc=$?
[ "$rc" -eq 0 ] && ok "main commit allowed when no run active" || bad "commit should pass with no run" "$rc"
hook "$CIGATE" "git push -f origin main" "$TMP"; rc=$?
[ "$rc" -eq 2 ] && ok "force-push to main denied even with no run" || bad "force push should be denied" "$rc"

echo
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
