#!/usr/bin/env bash
# Recall grader (the opt-in, live leg). The juror is spawned by Claude Code (via
# /jje or a direct juror invocation) against a case's fixture; this script GRADES
# the verdict it produced: did the owning juror flag the planted defect as
# blocking? A non-match is a false negative — feed it back into the review skill.
#
# Usage: tests/run-eval.sh <case-id> <path-to-verdict.json>
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CASE="${1:-}"; VERDICT="${2:-}"
[ -n "$CASE" ] && [ -f "$VERDICT" ] || { echo "usage: run-eval.sh <case-id> <verdict.json>"; exit 2; }

python3 - "$REPO" "$CASE" "$VERDICT" <<'PY'
import json, sys
repo, cid, vp = sys.argv[1], sys.argv[2], sys.argv[3]
cases = {c["id"]: c for c in json.load(open(f"{repo}/examples/eval/cases.json"))["cases"]}
if cid not in cases:
    print(f"unknown case '{cid}'"); sys.exit(2)
c = cases[cid]
v = json.load(open(vp))
blocking = [f for f in v.get("findings", []) if f.get("blocking")]
terms = [t.lower() for t in c["expect_match"]]
def hay(f): return " ".join(str(f.get(k, "")) for k in ("check", "issue", "evidence")).lower()
hit = any(any(t in hay(f) for t in terms) for f in blocking)
want = c["expect_blocking"]
if want and hit:
    print(f"PASS [{cid}] {c['juror']} flagged the planted defect ({c['planted_defect']})")
    sys.exit(0)
if want and not hit:
    print(f"FALSE NEGATIVE [{cid}] {c['juror']} did NOT flag: {c['planted_defect']}")
    print(f"  expected a blocking finding matching one of {c['expect_match']}; got {len(blocking)} blocking finding(s)")
    sys.exit(1)
print(f"[{cid}] expect_blocking={want}, blocking_found={bool(blocking)}")
sys.exit(0 if (bool(blocking) == want) else 1)
PY
