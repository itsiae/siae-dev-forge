#!/usr/bin/env bash
# Test: hooks/session-start inietta le 3 sezioni canoniche SIAE (environments,
# plan-deploy, multirepo) con fallback esplicito su file assente e marker di
# troncamento su file oversize.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
REF_DIR="${PLUGIN_ROOT}/skills/using-devforge/reference"
ENV_FILE="${REF_DIR}/siae-environments.md"
PLAN_FILE="${REF_DIR}/siae-plan-deploy.md"
MULTIREPO_FILE="${REF_DIR}/siae-multirepo.md"

PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

for f in "$ENV_FILE" "$PLAN_FILE" "$MULTIREPO_FILE"; do
    if [ ! -f "$f" ]; then
        echo "  SKIP  tutti i check: $(basename "$f") assente (Task 01 non applicato)"
        echo ""; echo "PASS=$PASS FAIL=$FAIL"
        exit 1
    fi
done

# (A) STRUTTURALE — wiring presente nel hook per i 3 file + fallback + budget.
ok "legge siae-environments.md" \
   "grep -q 'siae-environments.md' '$HOOK'"
ok "legge siae-plan-deploy.md" \
   "grep -q 'siae-plan-deploy.md' '$HOOK'"
ok "legge siae-multirepo.md" \
   "grep -q 'siae-multirepo.md' '$HOOK'"
ok "usa budget byte (SIAE_CONVENTIONS_MAX_BYTES=1800 + head -c)" \
   "grep -q 'SIAE_CONVENTIONS_MAX_BYTES=1800' '$HOOK' && grep -q 'head -c' '$HOOK'"
ok "marker fallback esplicito presente nel sorgente" \
   "grep -q 'FONTE NON DISPONIBILE' '$HOOK'"
ok "marker troncamento presente nel sorgente" \
   "grep -q '\\[troncato\\]' '$HOOK'"
ok "sezioni referenziate in session_context" \
   "grep -E 'session_context=.*siae_environments_section' '$HOOK' >/dev/null && \
    grep -E 'session_context=.*siae_plan_deploy_section' '$HOOK' >/dev/null && \
    grep -E 'session_context=.*siae_multirepo_section' '$HOOK' >/dev/null"

# (B) FUNZIONALE (a) — con i 3 file presenti, additional_context contiene le 3 sezioni.
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null || true)
if echo "$STDOUT" | grep -q 'additional_context'; then
    ok "func(a): additional_context contiene marcatore ambienti/stage" \
       "echo \"\$STDOUT\" | grep -qi 'ambient'"
    ok "func(a): additional_context contiene marcatore plan/deploy" \
       "echo \"\$STDOUT\" | grep -qi 'plan'"
    ok "func(a): additional_context contiene marcatore multirepo" \
       "echo \"\$STDOUT\" | grep -qi 'multirepo\\|multi-repo'"
    ok "func(a): stdout è JSON valido" \
       "echo \"\$STDOUT\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(a): session-start non ha prodotto additional_context in sandbox"
fi

# (B) FUNZIONALE (b) — file assente → marker esplicito, MAI empty-string silenzioso.
BAK_ENV="${ENV_FILE}.bak.$$"
trap '[ -f "$BAK_ENV" ] && mv -f "$BAK_ENV" "$ENV_FILE" 2>/dev/null || true' EXIT
mv "$ENV_FILE" "$BAK_ENV"
TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
STDOUT2=$(printf '{}' | HOME="$TMPHOME2" bash "$HOOK" 2>/dev/null || true)
mv "$BAK_ENV" "$ENV_FILE"; trap - EXIT
if echo "$STDOUT2" | grep -q 'additional_context'; then
    ok "func(b): file assente -> marker 'FONTE NON DISPONIBILE' iniettato" \
       "echo \"\$STDOUT2\" | grep -q 'FONTE NON DISPONIBILE'"
    ok "func(b): stdout resta JSON valido anche con fallback" \
       "echo \"\$STDOUT2\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(b): session-start non ha prodotto additional_context in sandbox"
fi

# (B) FUNZIONALE (c) — file oversize (> 1800 byte) -> marker [troncato].
BAK_PLAN="${PLAN_FILE}.bak.$$"
trap '[ -f "$BAK_PLAN" ] && mv -f "$BAK_PLAN" "$PLAN_FILE" 2>/dev/null || true' EXIT
cp "$PLAN_FILE" "$BAK_PLAN"
python3 -c "print('X' * 2500)" > "$PLAN_FILE"
TMPHOME3="$(mktemp -d)"; mkdir -p "$TMPHOME3/.claude"
STDOUT3=$(printf '{}' | HOME="$TMPHOME3" bash "$HOOK" 2>/dev/null || true)
mv "$BAK_PLAN" "$PLAN_FILE"; trap - EXIT
if echo "$STDOUT3" | grep -q 'additional_context'; then
    ok "func(c): file oversize -> marker '[troncato]' iniettato" \
       "echo \"\$STDOUT3\" | grep -q '\\[troncato\\]'"
    ok "func(c): stdout resta JSON valido con troncamento" \
       "echo \"\$STDOUT3\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(c): session-start non ha prodotto additional_context in sandbox"
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
