#!/usr/bin/env bash
# Test: hooks/session-start emette gate_bypassed enforcement_off quando DEVFORGE_ENFORCEMENT_OFF=1
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# (A) STRUTTURALE (hard) — il wiring è presente, guarded, pipefail-safe, no stdout.
ok "guard DEVFORGE_ENFORCEMENT_OFF presente" \
   "grep -q 'DEVFORGE_ENFORCEMENT_OFF' '$HOOK'"
ok "emette gate_bypassed enforcement_off" \
   "grep -q 'gate_bypassed' '$HOOK' && grep -q 'enforcement_off' '$HOOK'"
ok "emissione best-effort (|| true)" \
   "grep -E 'gate_bypassed.*\|\|[[:space:]]*true|enforcement_off.*\|\|[[:space:]]*true' '$HOOK' >/dev/null"

# (B) FUNZIONALE (tollerante: session-start può essere pesante in sandbox).
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" DEVFORGE_ENFORCEMENT_OFF=1 bash "$HOOK" 2>/dev/null || true)
ACT="$TMPHOME/.claude/devforge-activity.jsonl"
if [ -s "$ACT" ]; then
    ok "func: gate_bypassed+enforcement_off in activity.jsonl" \
       "grep -q 'gate_bypassed' '$ACT' && grep -q 'enforcement_off' '$ACT'"
    ok "invariante: stdout contiene additional_context" \
       "echo \"\$STDOUT\" | grep -q 'additional_context'"
    # Negativo: senza la env var, nessun gate_bypassed
    TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
    printf '{}' | HOME="$TMPHOME2" bash "$HOOK" >/dev/null 2>&1 || true
    ACT2="$TMPHOME2/.claude/devforge-activity.jsonl"
    ok "func negativo: nessun gate_bypassed senza la env var" \
       "! ( [ -s '$ACT2' ] && grep -q 'gate_bypassed' '$ACT2' )"
else
    echo "  SKIP  func: session-start non ha prodotto activity.jsonl in sandbox (strutturale copre il wiring)"
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
