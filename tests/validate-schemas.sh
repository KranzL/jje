#!/usr/bin/env bash
# Validates that the JSON Schemas parse and that the verdict-contract example
# validates against the verdict schema (when jsonschema is installed).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMADIR="$REPO/.claude/skills/jje/schemas"
PASS=0; FAIL=0
ok() { echo "  ok: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

for s in verdict decision plan; do
  if python3 -c "import json;json.load(open('$SCHEMADIR/$s.schema.json'))" 2>/dev/null; then
    ok "$s.schema.json parses"
  else
    bad "$s.schema.json does not parse"
  fi
done

# An example verdict that must satisfy the verdict schema.
EX="$(mktemp)"
cat > "$EX" <<'EOF'
{"juror":"security-juror","category":"security",
 "findings":[{"id":"sec-sqli-handler.go:142","check":"semgrep:sqli",
 "severity":"error","blocking":true,"issue":"sqli in handler.go:142",
 "evidence":"semgrep @ handler.go:142","suggested_fix":"parameterize"}],
 "ran":["semgrep"],"skipped":[]}
EOF

if python3 -c "import jsonschema" 2>/dev/null; then
  if python3 -c "
import json,jsonschema
schema=json.load(open('$SCHEMADIR/verdict.schema.json'))
inst=json.load(open('$EX'))
jsonschema.validate(inst,schema)
" 2>/dev/null; then
    ok "example verdict validates against verdict.schema.json"
  else
    bad "example verdict failed schema validation"
  fi
else
  echo "  skip: jsonschema not installed (pip install jsonschema for full validation)"
fi
rm -f "$EX"

echo
echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
