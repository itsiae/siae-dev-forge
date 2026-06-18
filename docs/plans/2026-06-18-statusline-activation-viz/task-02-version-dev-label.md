# Task 02 — A+B: label versione / dev-mode (statusline)

**Stato:** [PENDING]
**File:** `tests/statusline/test_statusline_version_label.sh` (nuovo), `statusline/devforge-statusline.sh`
**AC coperti:** AC-A, AC-B
**Stima:** Umano ~1 · Augmented ~0.5

## Ciclo TDD

### RED — nuovo test

Crea `tests/statusline/test_statusline_version_label.sh`. Per controllare la versione vista dallo statusline si manipola la posizione dello script: lo statusline calcola `PLUGIN_ROOT_SL` come `dirname(script)/..`. Il test copia lo statusline in una struttura fittizia `<tmp>/<versione>/statusline/devforge-statusline.sh` e lo invoca da lì, così `basename PLUGIN_ROOT_SL` = `<versione>`.

```bash
#!/usr/bin/env bash
# Test: label riga 1 mostra versione (semver) o (dev) (Feature A/B)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

# Copia lo statusline (+ lib, che viene sourcato) in <tmp>/<verdir>/ e ritorna il path dello script
stage_at_version() { # verdir
  local tmp; tmp="$(mktemp -d)"
  mkdir -p "$tmp/$1/statusline" "$tmp/$1/lib"
  cp "$REAL_STATUSLINE" "$tmp/$1/statusline/devforge-statusline.sh"
  cp "$(cd "$SCRIPT_DIR/../../lib" && pwd)"/*.sh "$tmp/$1/lib/" 2>/dev/null || true
  printf '%s' "$tmp/$1/statusline/devforge-statusline.sh"
}

# --- Caso A: versione semver -> "DevForge v1.91.0" ---
S1="$(stage_at_version "1.91.0")"
OUT1="$(printf '{}' | bash "$S1" 2>/dev/null | head -1 || true)"
if printf '%s' "$OUT1" | grep -q "DevForge v1.91.0"; then
  PASS=$((PASS+1)); echo "  PASS  semver -> DevForge v1.91.0"
else
  FAIL=$((FAIL+1)); echo "  FAIL  semver (out: $OUT1)"
fi
rm -rf "$(dirname "$(dirname "$(dirname "$S1")")")"

# --- Caso B: non-semver (dev) -> "DevForge (dev)" ---
S2="$(stage_at_version "siae-dev-forge")"
OUT2="$(printf '{}' | bash "$S2" 2>/dev/null | head -1 || true)"
if printf '%s' "$OUT2" | grep -q "DevForge (dev)"; then
  PASS=$((PASS+1)); echo "  PASS  non-semver -> DevForge (dev)"
else
  FAIL=$((FAIL+1)); echo "  FAIL  dev-mode (out: $OUT2)"
fi
# Caso B non deve mostrare una versione
if printf '%s' "$OUT2" | grep -qE "DevForge v[0-9]"; then
  FAIL=$((FAIL+1)); echo "  FAIL  dev-mode mostra erroneamente una versione"
else
  PASS=$((PASS+1)); echo "  PASS  dev-mode senza versione"
fi
rm -rf "$(dirname "$(dirname "$(dirname "$S2")")")"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui → DEVE fallire (label oggi è solo "🔨 DevForge").

### GREEN — implementa in statusline

`PLUGIN_ROOT_SL` è calcolato a riga 132. Dopo quel calcolo (o subito prima della composizione LINE1), determina la versione. Poi modifica la riga 236.

Aggiungi (dopo la lettura del flag plugin-updated, ~riga 155, dove le variabili sono disponibili):
```bash
# Versione plugin per il label (A/B): semver da basename PLUGIN_ROOT_SL, altrimenti dev-mode
PLUGIN_LABEL_VER=""
PLUGIN_IS_DEV=0
_pv="$(basename "$PLUGIN_ROOT_SL" 2>/dev/null)"
if printf '%s' "$_pv" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  PLUGIN_LABEL_VER="$_pv"
else
  PLUGIN_IS_DEV=1
fi
unset _pv
```

Sostituisci la riga 236 `LINE1="🔨 DevForge"` con:
```bash
LINE1="🔨 DevForge"
if [ -n "$PLUGIN_LABEL_VER" ]; then
  LINE1="${LINE1} v${PLUGIN_LABEL_VER}"
elif [ "$PLUGIN_IS_DEV" -eq 1 ]; then
  LINE1="${LINE1} (dev)"
fi
```

Riesegui test → PASS=4 FAIL=0.

### REFACTOR
Nessuno.

## Criteri di completamento
- [ ] `test_statusline_version_label.sh` PASS=4 FAIL=0
- [ ] semver → `🔨 DevForge vX.Y.Z`
- [ ] non-semver → `🔨 DevForge (dev)` senza versione
- [ ] mutua esclusività rispettata
