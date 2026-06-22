#!/usr/bin/env bash
# Test P-banner: devforge_python3_banner + wiring in session-start.
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
P=0; F=0
ok(){ if [ "$2" = "$3" ]; then echo "  PASS $1"; P=$((P+1)); else echo "  FAIL $1: [$2]!=[$3]"; F=$((F+1)); fi; }
has(){ case "$2" in *"$3"*) echo "  PASS $1"; P=$((P+1));; *) echo "  FAIL $1: manca [$3]"; F=$((F+1));; esac; }
BASH_BIN="$(command -v bash)"

# ASSENTE: PATH vuoto → command -v python3 fallisce → banner esplicito (solo builtin: printf/command).
# bash invocato con path assoluto perché con PATH= il lookup di 'bash' fallirebbe.
A=$(PATH= "$BASH_BIN" -c 'source "'"$REPO"'/lib/python3-check.sh"; devforge_python3_banner')
has "ASSENTE: banner avvisa" "$A" "python3 NON"
has "ASSENTE: comando install" "$A" "brew install python3"

# PRESENTE: python3 sul PATH → banner vuoto (skip se l'ambiente di test non ha python3)
if command -v python3 >/dev/null 2>&1; then
  B=$(bash -c 'source "'"$REPO"'/lib/python3-check.sh"; devforge_python3_banner')
  ok "PRESENTE: banner vuoto" "$B" ""
else
  echo "  SKIP PRESENTE (python3 assente nell'ambiente di test)"
fi

# WIRING: session-start sorgia il check e inietta il banner
W1=$(grep -c "python3-check.sh" "$REPO/hooks/session-start" 2>/dev/null || true); W1=${W1:-0}
ok "WIRING: source python3-check.sh" "$([ "$W1" -ge 1 ] && echo yes || echo no)" "yes"
W2=$(grep -c "python3_banner_section" "$REPO/hooks/session-start" 2>/dev/null || true); W2=${W2:-0}
ok "WIRING: banner in session_context" "$([ "$W2" -ge 2 ] && echo yes || echo no)" "yes"

echo "PASS=$P FAIL=$F"; [ "$F" -eq 0 ]
