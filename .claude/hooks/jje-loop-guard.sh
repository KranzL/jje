#!/usr/bin/env bash
# PreToolUse hook (matcher: Agent|Task). Deterministic, MODEL-INDEPENDENT
# backstop for the iteration budget and the oscillation guard.
#
# It fires on every Executor spawn and maintains its OWN counter, so a runaway
# orchestrator that "forgets" to call `jje_state.py start-iteration` still
# cannot re-spawn the Executor past the budget. The authoritative business
# counter stays in run.json; this hook is the independent cap.
set -euo pipefail

INPUT="$(cat)"
PROJ="${CLAUDE_PROJECT_DIR:-$PWD}"

# Tool input field is `subagent_type` on both the Agent and the (legacy) Task
# spawn tool; accept either spelling defensively.
SUBAGENT="$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // .tool_input.subagentType // ""' 2>/dev/null || echo "")"
[ "$SUBAGENT" = "executor" ] || exit 0

# Resolve the active run from the lock (single active run is enforced by init).
RUN_DIR=""
if [ -f "$PROJ/.jje/ACTIVE" ]; then
  RUN_DIR="$(jq -r '.run_dir // ""' "$PROJ/.jje/ACTIVE" 2>/dev/null || echo "")"
  case "$RUN_DIR" in /*) ;; *) [ -n "$RUN_DIR" ] && RUN_DIR="$PROJ/$RUN_DIR" ;; esac
fi
[ -n "$RUN_DIR" ] && [ -d "$RUN_DIR" ] || RUN_DIR="$(ls -dt "$PROJ"/.jje/runs/*/ 2>/dev/null | head -1 || true)"
[ -n "$RUN_DIR" ] || exit 0
RUN_JSON="$RUN_DIR/run.json"
[ -f "$RUN_JSON" ] || exit 0

deny() { printf '{"decision":"deny","reason":%s}\n' "$(jq -Rn --arg m "$1" '$m')"; exit 2; }

BUDGET="$(jq -r '.budget' "$RUN_JSON" 2>/dev/null || echo 6)"

# --- model-independent spawn counter ----------------------------------------
COUNTER="$RUN_DIR/executor-spawns"
COUNT="$(cat "$COUNTER" 2>/dev/null || echo 0)"
COUNT=$((COUNT + 1))
printf '%s' "$COUNT" > "$COUNTER"
if [ "$COUNT" -gt "$BUDGET" ]; then
  deny "JJE: hard spawn cap reached ($BUDGET Executor spawns). Route to ESCALATE; the budget is spent."
fi

# --- authoritative business counter (advisory cross-check) ------------------
ITER="$(jq -r '.iteration' "$RUN_JSON" 2>/dev/null || echo 0)"
if [ "$ITER" -ge "$BUDGET" ]; then
  deny "JJE: iteration budget ($BUDGET) exhausted. Route to ESCALATE, do not re-spawn the Executor."
fi

# --- oscillation guard ------------------------------------------------------
LEDGER="$RUN_DIR/ledger.json"
if [ -f "$LEDGER" ]; then
  RECUR="$(jq '[.findings[] | select((.iterations|length) >= 2)] | length' "$LEDGER" 2>/dev/null || echo 0)"
  CONTRA="$(jq '.contradictions | length' "$LEDGER" 2>/dev/null || echo 0)"
  if [ "${RECUR:-0}" -gt 0 ] || [ "${CONTRA:-0}" -gt 0 ]; then
    deny "JJE: oscillation guard tripped (recurring blocking finding or contradictory pair). Route to ESCALATE."
  fi
fi
exit 0
