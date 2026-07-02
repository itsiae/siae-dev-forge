#!/usr/bin/env bash
# Test: hooks/convention-injector inietta la convenzione pertinente ai 3 momenti clou,
# con dedup, passthrough su prompt irrilevante e marker esplicito su fonte mancante.
# HOME fresco per chiamata -> isola lo state di dedup tra i casi.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="$PLUGIN_ROOT/hooks/convention-injector"
REF="$PLUGIN_ROOT/skills/using-devforge/reference"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }
emit(){ local h; h=$(mktemp -d); printf '%s' "$1" | HOME="$h" bash "$HOOK" 2>/dev/null; rm -rf "$h"; }

echo "TEST convention-injector"

# Trigger 1: prompt di deploy -> inietta environments + plan-deploy
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"facciamo il deploy in collaudo con terragrunt"}')
ok "T1: trigger deploy inietta contesto ambienti/plan" \
   "printf '%s' \"\$OUT\" | grep -qi 'ambient\\|stage\\|collaudo\\|PLAN'"

# Trigger 2: edit IaC -> inietta multirepo + environments
OUT=$(emit '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"modules/net/main.tf"}}')
ok "T2: trigger IaC inietta multirepo" \
   "printf '%s' \"\$OUT\" | grep -qi 'iac\\|bff\\|spa\\|multi-repo\\|multirepo'"

# Trigger 3: promozione ambiente (git tag) -> inietta plan-deploy
OUT=$(emit '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git tag collaudo && git push origin collaudo"}}')
ok "T3: trigger promozione inietta plan-deploy" \
   "printf '%s' \"\$OUT\" | grep -qi 'gate\\|progressione\\|certificazione\\|PLAN'"

# Non-trigger: prompt irrilevante -> nessuna iniezione
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"come stai oggi"}')
ok "T4: no-inject su prompt irrilevante" \
   "[ \"\$(printf '%s' \"\$OUT\" | tr -d '[:space:]')\" = '{}' ]"

# JSON valido su un trigger
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"deploy in produzione"}')
ok "T5: output JSON valido" \
   "printf '%s' \"\$OUT\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"

# Fonte mancante -> marker esplicito
BAK="${REF}/siae-plan-deploy.md.bak.$$"
trap '[ -f "$BAK" ] && mv -f "$BAK" "${REF}/siae-plan-deploy.md" 2>/dev/null || true' EXIT
mv "${REF}/siae-plan-deploy.md" "$BAK"
OUT=$(emit '{"hook_event_name":"UserPromptSubmit","prompt":"deploy release"}')
mv "$BAK" "${REF}/siae-plan-deploy.md"; trap - EXIT
ok "T6: fonte mancante -> marker FONTE NON DISPONIBILE" \
   "printf '%s' \"\$OUT\" | grep -q 'FONTE NON DISPONIBILE'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
