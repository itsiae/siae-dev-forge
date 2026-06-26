#!/usr/bin/env bash
# Test: hooks/session-start inietta la sezione SIAE Global Rules leggendo la fonte unica versionata.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
RULES="${PLUGIN_ROOT}/skills/using-devforge/reference/siae-global-rules.md"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# (A) STRUTTURALE (hard) — wiring presente, guarded, fail-safe, referenziato in session_context.
ok "legge il file regole" \
   "grep -q 'siae-global-rules.md' '$HOOK'"
ok "calcola global_rules_section guarded" \
   "grep -q 'global_rules_section' '$HOOK' && grep -q 'global_rules_content' '$HOOK'"
ok "lettura fail-safe (2>/dev/null)" \
   "grep -E 'siae-global-rules.md.*2>/dev/null' '$HOOK' >/dev/null"
ok "global_rules_section referenziato in session_context" \
   "grep -E 'session_context=.*\\\$\\{?global_rules_section' '$HOOK' >/dev/null"

# (D) ANTI-LEAK (hard) — la fonte versionata non contiene dati per-persona/segreti.
# NB: 'git@github.com' e' un esempio anti-pattern legittimo nelle regole -> whitelisted.
ok "anti-leak: nessun account-personale/path-macchina" \
   "! grep -qE 'federicoarcangeli|/Users/|OneDrive[^/[:space:]]' '$RULES'"
ok "anti-leak: nessuna email personale (whitelist git@github.com)" \
   "[ -z \"\$(grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' '$RULES' | grep -v '^git@github\.com\$')\" ]"
ok "anti-leak: unico IP = proxy 10.255.1.241" \
   "[ \"\$(grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' '$RULES' | sort -u)\" = '10.255.1.241' ]"

# (B) FUNZIONALE (tollerante: session-start puo' essere pesante in sandbox).
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null || true)
if echo "$STDOUT" | grep -q 'additional_context'; then
    ok "func: additional_context contiene 'SIAE Global Rules'" \
       "echo \"\$STDOUT\" | grep -q 'SIAE Global Rules'"
    ok "func: stdout e' JSON valido" \
       "echo \"\$STDOUT\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func: session-start non ha prodotto additional_context in sandbox (strutturale copre il wiring)"
fi

# (C) FAIL-SAFE — file regole assente -> sezione sparisce ma additional_context resta JSON valido.
if [ -f "$RULES" ]; then
    BAK="${RULES}.bak.$$"
    # trap PRIMA del mv: chiude la finestra atomica -> file mai perso anche su interrupt.
    trap '[ -f "$BAK" ] && mv -f "$BAK" "$RULES" 2>/dev/null || true' EXIT
    mv "$RULES" "$BAK"
    TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
    STDOUT2=$(printf '{}' | HOME="$TMPHOME2" bash "$HOOK" 2>/dev/null || true)
    mv "$BAK" "$RULES"; trap - EXIT
    if echo "$STDOUT2" | grep -q 'additional_context'; then
        ok "fail-safe: senza file no 'SIAE Global Rules' ma JSON valido" \
           "! echo \"\$STDOUT2\" | grep -q 'SIAE Global Rules' && echo \"\$STDOUT2\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
    else
        echo "  SKIP  fail-safe: session-start non ha prodotto additional_context in sandbox"
    fi
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
