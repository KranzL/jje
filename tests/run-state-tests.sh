#!/usr/bin/env bash
# Exercises the deterministic core of jje_state.py: the run lock, the iteration
# budget, the oscillation fingerprint, and the CI-validated accept gate.
# No LLM involved — this is the part that must be trustworthy.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$REPO/.claude/scripts/jje_state.py"
PASS=0; FAIL=0
ok()   { echo "  ok: $1"; PASS=$((PASS+1)); }
bad()  { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PROJECT_DIR="$TMP"
S() { python3 "$STATE" "$@"; }
jget() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$1" "$2"; }
field() { python3 -c "import json,sys;print(json.loads(sys.stdin.read())[sys.argv[1]])" "$1"; }

echo "== init + run lock =="
OUT="$(S init --request "test run" --budget 2)"
RUN="$(printf '%s' "$OUT" | field run_dir)"
[ -d "$RUN" ] && ok "init created run dir" || bad "no run dir"
[ -f "$CLAUDE_PROJECT_DIR/.jje/ACTIVE" ] && ok "ACTIVE lock written" || bad "no ACTIVE lock"
if S init --request "second" >/dev/null 2>&1; then bad "second init should be refused"; else ok "second init refused (lock held)"; fi
RUNABS="$RUN"

echo "== iteration budget (budget=2) =="
S start-iteration --run "$RUNABS" >/dev/null && ok "start-iteration 1" || bad "start 1"
S start-iteration --run "$RUNABS" >/dev/null && ok "start-iteration 2" || bad "start 2"
if S start-iteration --run "$RUNABS" >/dev/null 2>&1; then bad "3rd start should be refused (budget)"; else ok "budget exhausted refuses 3rd iteration"; fi

echo "== oscillation guard (same defect, new id+line across iters) =="
TMP2="$(mktemp -d)"; export CLAUDE_PROJECT_DIR="$TMP2"
OUT="$(S init --request osc --budget 6)"; RUN="$(printf '%s' "$OUT" | field run_dir)"; RUNABS="$RUN"
write_verdict() { # $1=iter $2=line $3=id
  mkdir -p "$RUNABS/iterations/iter-$1/verdicts"
  cat > "$RUNABS/iterations/iter-$1/verdicts/security-juror.json" <<EOF
{"juror":"security-juror","category":"security","ran":["semgrep"],"skipped":[],
 "findings":[{"id":"$3","check":"semgrep:sqli","severity":"error","blocking":true,
 "issue":"sqli in handler.go:$2","evidence":"semgrep @ handler.go:$2"}]}
EOF
}
S start-iteration --run "$RUNABS" >/dev/null
write_verdict 1 142 sec-1
G1="$(S check-guards --run "$RUNABS")"
[ "$(printf '%s' "$G1" | field recommend_escalate)" = "False" ] && ok "iter1 not yet recurring" || bad "iter1 wrongly recurring"
S start-iteration --run "$RUNABS" >/dev/null
write_verdict 2 148 sec-9
G2="$(S check-guards --run "$RUNABS")"
[ "$(printf '%s' "$G2" | field recommend_escalate)" = "True" ] && ok "iter2 recurring → escalate (id+line ignored)" || bad "iter2 should recommend escalate"

echo "== CI-validated accept gate =="
TMP3="$(mktemp -d)"; export CLAUDE_PROJECT_DIR="$TMP3"
OUT="$(S init --request acc --budget 6)"; RUN="$(printf '%s' "$OUT" | field run_dir)"; RUNABS="$RUN"
S start-iteration --run "$RUNABS" >/dev/null
S record-decision --run "$RUNABS" --decision ACCEPT >/dev/null
if S accept --run "$RUNABS" >/dev/null 2>&1; then bad "accept should refuse without ci-result"; else ok "accept refuses without CI artifact"; fi
ITERDIR="$RUNABS/iterations/iter-1"
python3 -c "import json,time;json.dump({'command':'make ci','exit_code':1,'sha':'abc','ts':time.time()},open('$ITERDIR/ci-result.json','w'))"
if S accept --run "$RUNABS" >/dev/null 2>&1; then bad "accept should refuse on CI exit!=0"; else ok "accept refuses on red CI"; fi
python3 -c "import json,time;json.dump({'command':'make ci','exit_code':0,'sha':'abc123','ts':time.time()},open('$ITERDIR/ci-result.json','w'))"
if S accept --run "$RUNABS" >/dev/null 2>&1; then ok "accept succeeds on green CI artifact"; else bad "accept should succeed on green CI"; fi
[ -f "$CLAUDE_PROJECT_DIR/.jje/COMMIT_APPROVED" ] && ok "COMMIT_APPROVED marker written" || bad "no marker after accept"

echo
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
