# Task 04 — C: pallino 🟡 fallback telemetria (statusline)

**Stato:** [PENDING]
**File:** `tests/statusline/test_statusline_telemetry_health.sh` (nuovo), `statusline/devforge-statusline.sh`
**AC coperti:** AC-C
**Stima:** Umano ~0.5 · Augmented ~0.25
**Dipende da:** task-02 (la composizione del label con versione deve esistere; il 🟡 va dopo la versione/(dev))

## Ciclo TDD

### RED — nuovo test

Crea `tests/statusline/test_statusline_telemetry_health.sh`. Verifica: sentinel `~/.claude/.devforge-no-fsync-warned` presente → riga 1 contiene `🟡`; assente → no `🟡`.

```bash
#!/usr/bin/env bash
# Test: pallino 🟡 sul label quando telemetria in fallback (sentinel presente) (Feature C)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

render_home() { # home
  printf '{}' | HOME="$1" bash "$STATUSLINE" 2>/dev/null | head -1
}

# --- Caso 1: sentinel presente -> 🟡 ---
H1="$(mktemp -d)"; mkdir -p "$H1/.claude"; touch "$H1/.claude/.devforge-no-fsync-warned"
OUT1="$(render_home "$H1")"
if printf '%s' "$OUT1" | grep -q "🟡"; then PASS=$((PASS+1)); echo "  PASS  sentinel -> 🟡"; else FAIL=$((FAIL+1)); echo "  FAIL  sentinel senza 🟡 (out: $OUT1)"; fi
rm -rf "$H1"

# --- Caso 2: sentinel assente -> no 🟡 ---
H2="$(mktemp -d)"; mkdir -p "$H2/.claude"
OUT2="$(render_home "$H2")"
if printf '%s' "$OUT2" | grep -q "🟡"; then FAIL=$((FAIL+1)); echo "  FAIL  nessun sentinel ma 🟡 mostrato"; else PASS=$((PASS+1)); echo "  PASS  nessun sentinel -> no 🟡"; fi
rm -rf "$H2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui → DEVE fallire (il pallino non esiste ancora).

### GREEN — implementa in statusline

Dopo il blocco che determina `PLUGIN_LABEL_VER`/`PLUGIN_IS_DEV` (task-02), aggiungi la lettura del sentinel:
```bash
# Salute telemetria (C): sentinel scritto da logger.sh quando il path fsync degrada a bash
TELEMETRY_DOT=""
if [ -f "${DEVFORGE_DIR}/.devforge-no-fsync-warned" ]; then
  TELEMETRY_DOT="🟡"
fi
```

Nella composizione del label (subito dopo il blocco versione/dev di task-02, PRIMA del primo `| ${GIT_BRANCH}`), aggiungi:
```bash
if [ -n "$TELEMETRY_DOT" ]; then
  LINE1="${LINE1} ${TELEMETRY_DOT}"
fi
```

Riesegui test → PASS=2 FAIL=0.

### REFACTOR
Nessuno.

## Criteri di completamento
- [ ] `test_statusline_telemetry_health.sh` PASS=2 FAIL=0
- [ ] sentinel presente → 🟡 sul label (dopo versione/(dev), prima del branch)
- [ ] sentinel assente → nessun 🟡
- [ ] warning python3 esistente (#339) non soppresso (co-presenza ok)
