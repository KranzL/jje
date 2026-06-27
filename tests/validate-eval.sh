#!/usr/bin/env bash
# Structural validation of the eval corpus (no LLM): cases.json parses, every
# fixture directory exists, and every juror named by a case is registered in the
# config. The live recall harness (tests/run-eval.sh) is separate and opt-in.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$REPO" <<'PY'
import json, os, sys
repo = sys.argv[1]
cases = json.load(open(os.path.join(repo, "examples", "eval", "cases.json")))["cases"]
cfg = json.load(open(os.path.join(repo, ".jje", "config.example.json")))
jurors = cfg.get("jurors", {})
fail = 0
def bad(m):
    global fail; fail += 1; print("  FAIL:", m)
def ok(m): print("  ok:", m)

seen = set()
for c in cases:
    cid = c.get("id", "?")
    if cid in seen:
        bad(f"duplicate case id '{cid}'")
    seen.add(cid)
    for k in ("id", "lane", "juror", "fixture", "expect_blocking", "expect_match"):
        if k not in c:
            bad(f"case '{cid}' missing field '{k}'"); break
    else:
        if c["juror"] not in jurors:
            bad(f"case '{cid}' names unregistered juror '{c['juror']}'")
        elif not os.path.isdir(os.path.join(repo, c["fixture"])):
            bad(f"case '{cid}' fixture missing: {c['fixture']}")
        elif not isinstance(c["expect_match"], list) or not c["expect_match"]:
            bad(f"case '{cid}' expect_match must be a non-empty list")
        else:
            ok(f"case '{cid}': juror '{c['juror']}' + fixture present")

print()
print(f"== {len(cases)} cases, {'OK' if not fail else str(fail)+' FAILURES'} ==")
sys.exit(1 if fail else 0)
PY
