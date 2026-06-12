#!/usr/bin/env bash
# No-regression payload commit_created + integrazione hooks.json (task-03)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

HOOK="$PLUGIN_ROOT/hooks/post-commit-review"

# T9a — la riga del payload commit_created (contiene commit_sha + tests_files_changed) ha TUTTI i campi pre-esistenti
PAYLOAD=$(grep 'commit_sha' "$HOOK" | grep 'tests_files_changed' | head -1)
[ -n "$PAYLOAD" ] || ko "T9a payload" "riga payload non trovata"
for field in commit_sha files_changed insertions deletions has_tests; do
  echo "$PAYLOAD" | grep -q "\\\\\"$field\\\\\"" && ok "T9a campo: $field" || ko "T9a $field" "mancante"
done

# T9b — campo nuovo + has_tests ancora boolean (interpolazione ${HAS_TESTS}, non quotata)
echo "$PAYLOAD" | grep -q 'tests_files_changed' && ok "T9b tests_files_changed presente" || ko "T9b" "campo nuovo mancante"
# has_tests boolean = interpolato nudo ':${HAS_TESTS}' (NON quotato ':"${HAS_TESTS}"')
echo "$PAYLOAD" | grep -qE ':\$\{HAS_TESTS\}' && ! echo "$PAYLOAD" | grep -qE '"\$\{HAS_TESTS\}"' \
  && ok "T9b has_tests boolean (non quotato)" || ko "T9b has_tests" "non boolean/quotato"

# T9c — hooks.json valido + branch-tracker presente
python3 -c 'import json;json.load(open("'"$PLUGIN_ROOT"'/hooks/hooks.json"))' 2>/dev/null && ok "T9c hooks.json valido" || ko "T9c" "JSON invalido"
grep -q 'branch-tracker' "$PLUGIN_ROOT/hooks/hooks.json" && ok "T9c branch-tracker registrato" || ko "T9c bt" "non in hooks.json"

# T9d — branch-tracker SOLO in PostToolUse Bash
RES=$(python3 - "$PLUGIN_ROOT/hooks/hooks.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
post_bash=False; elsewhere=False
for grp in d.get("hooks",{}).get("PostToolUse",[]):
    if grp.get("matcher")=="Bash":
        for h in grp.get("hooks",[]):
            if "branch-tracker" in h.get("command",""): post_bash=True
for ev in ("PreToolUse","Stop","SessionStart","UserPromptSubmit"):
    for grp in d.get("hooks",{}).get(ev,[]):
        for h in grp.get("hooks",[]):
            if "branch-tracker" in h.get("command",""): elsewhere=True
print("OK" if (post_bash and not elsewhere) else "FAIL")
PY
)
[ "$RES" = "OK" ] && ok "T9d branch-tracker solo PostToolUse Bash" || ko "T9d" "res=$RES"

echo "no-regression: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
