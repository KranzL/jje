#!/usr/bin/env bash
# Verifies the roster wiring: every preset references a registered juror, every
# registered juror's agent file and review skill exist on disk, and every juror
# agent's `name:` frontmatter matches its config id. This catches the silent
# "seats no one" failure mode where a config id and an agent name drift apart.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$REPO" <<'PY'
import json, os, sys, re
repo = sys.argv[1]
cfg = json.load(open(os.path.join(repo, ".jje", "config.example.json")))
jurors = cfg.get("jurors", {})
presets = cfg.get("presets", {})
fail = 0
def bad(m):
    global fail; fail += 1; print("  FAIL:", m)
def ok(m): print("  ok:", m)

for name, preset in presets.items():
    for jid in preset:
        if jid not in jurors:
            bad(f"preset '{name}' references unregistered juror '{jid}'")
    else:
        ok(f"preset '{name}' references only registered jurors")

for jid, j in jurors.items():
    agent = j.get("agent")
    skill = j.get("skill")
    apath = os.path.join(repo, ".claude", "agents", "jurors", f"{agent}.md")
    spath = os.path.join(repo, ".claude", "skills", skill, "SKILL.md")
    if not os.path.exists(apath):
        bad(f"juror '{jid}': agent file missing ({apath})")
        continue
    if not os.path.exists(spath):
        bad(f"juror '{jid}': review skill missing ({spath})")
        continue
    head = open(apath).read()
    m = re.search(r"^name:\s*(\S+)", head, re.M)
    if not m or m.group(1) != agent:
        bad(f"juror '{jid}': agent name frontmatter '{m and m.group(1)}' != '{agent}'")
    else:
        ok(f"juror '{jid}': agent + skill present, name matches")

print()
print(f"== {'OK' if not fail else str(fail)+' FAILURES'} ==")
sys.exit(1 if fail else 0)
PY
