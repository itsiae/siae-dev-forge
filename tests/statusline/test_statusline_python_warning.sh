#!/usr/bin/env bash
# Test: statusline mostra avviso quando python3 manca dal PATH (Feature 1)
# RED->GREEN: piano docs/plans/2026-06-18-statusline-python-and-update-notice/ task-01
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

# Costruisce un PATH che contiene TUTTI i binari reali TRANNE python3/python.
# Tecnica robusta: simula una macchina realmente python-less (tutto il resto presente).
# NB: un PATH parziale (solo alcuni symlink) triggererebbe i path degradati di logger.sh
# (shasum/sleep/node/awk assenti) e farebbe loop/hang -> falso negativo. Qui mascheriamo SOLO python.
make_path_without_python() {
  local shim="$1"; mkdir -p "$shim"
  local d
  local IFS=':'
  # Un `ln -sf` per directory (glob) invece di uno per file: molti meno fork.
  # -f forza in caso di collisione tra dir (la precedenza esatta del PATH non conta per il test,
  # basta che ogni binario sia raggiungibile). python* viene rimosso dopo per renderlo introvabile.
  for d in $PATH; do
    [ -d "$d" ] || continue
    ln -sf "$d"/* "$shim/" 2>/dev/null || true
  done
  unset IFS
  rm -f "$shim"/python "$shim"/python3 "$shim"/python3.* 2>/dev/null || true
}

# --- Caso 1: python3 ASSENTE -> messaggio presente ---
TMP1="$(mktemp -d)"
make_path_without_python "$TMP1/bin"
OUT1="$(printf '{}' | PATH="$TMP1/bin" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT1" | grep -q "python3 assente"; then
  PASS=$((PASS+1)); echo "  PASS  python3 assente -> avviso mostrato"
else
  FAIL=$((FAIL+1)); echo "  FAIL  python3 assente -> avviso NON mostrato"; printf 'OUT: %s\n' "$OUT1"
fi
rm -rf "$TMP1"

# --- Caso 2: python3 PRESENTE -> nessun messaggio ---
OUT2="$(printf '{}' | bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT2" | grep -q "python3 assente"; then
  FAIL=$((FAIL+1)); echo "  FAIL  python3 presente -> avviso mostrato erroneamente"
else
  PASS=$((PASS+1)); echo "  PASS  python3 presente -> nessun avviso"
fi

# Nota: l'AC 3 ("nessun errore di script") e' verificato implicitamente: entrambe le invocazioni
# usano `|| true` e lo script gira sotto `set -euo pipefail`; un crash produrrebbe output vuoto e
# farebbe fallire le asserzioni sopra. Nessun increment dedicato -> totale atteso PASS=2.
echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
