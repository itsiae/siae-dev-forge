# Task 01 — D2: tier perl fsync in logger.sh (elimina degradazione)

**Stato:** [PENDING]
**File:** `tests/zero-loss/unit/test_logger_perl_fsync.sh` (nuovo), `lib/logger.sh`, `tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh` (aggiorna T3b/T9b)
**AC coperti:** AC-D2 (1-5)
**Stima:** Umano ~2 · Augmented ~1

## Ciclo TDD

### RED — nuovo test

Crea `tests/zero-loss/unit/test_logger_perl_fsync.sh`. Verifica due scenari del path di `_devforge_lock_append`:
- **Caso 1 (perl tier durabile):** python3+node mascherati, perl presente → la riga è scritta E `telemetry_degraded` NON è emesso (path durabile via perl).
- **Caso 2 (ultima spiaggia):** python3+node+perl tutti mascherati → riga scritta, uno shim `sync` in PATH è invocato (marker), `telemetry_degraded` emesso + sentinel scritto.

```bash
#!/usr/bin/env bash
# Test: _devforge_lock_append usa perl (fsync) quando python3+node assenti; bash+sync solo se anche perl assente
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0

make_mask() { # dir bins-to-mask...  -> crea shim con tutti i binari reali tranne quelli mascherati
  local shim="$1"; shift; local mask=" $* "; mkdir -p "$shim"
  local d; local IFS=':'
  for d in $PATH; do [ -d "$d" ] || continue; ln -sf "$d"/* "$shim/" 2>/dev/null || true; done
  unset IFS
  local b; for b in $mask; do rm -f "$shim/$b"; done
}

run_append() { # home shim_path
  local home="$1" shim="$2"
  HOME="$home" DEVFORGE_LOG_FILE="$home/.claude/devforge-activity.jsonl" \
  DEVFORGE_SESSION_DIR="$home/.claude/sess" \
  PATH="$shim" bash -c '
    set -euo pipefail
    source "'"$PLUGIN_ROOT"'/lib/logger.sh" 2>/dev/null || true
    _devforge_lock_append "'"$home"'/.claude/target.jsonl" "{\"event\":\"x\"}"$'"'"'\n'"'"'
  ' 2>/dev/null || true
}

# --- Caso 1: perl presente (python3+node mascherati) -> durabile, NO telemetry_degraded ---
T1="$(mktemp -d)"; mkdir -p "$T1/.claude/sess"
make_mask "$T1/bin" python python3 node
run_append "$T1" "$T1/bin"
line_ok=$([ -s "$T1/.claude/target.jsonl" ] && echo 1 || echo 0)
deg=$(grep -c 'telemetry_degraded' "$T1/.claude/devforge-activity.jsonl" 2>/dev/null || true); deg="${deg//[!0-9]/}"; deg="${deg:-0}"
if [ "$line_ok" = "1" ] && [ "$deg" = "0" ] && [ ! -f "$T1/.claude/.devforge-no-fsync-warned" ]; then
  PASS=$((PASS+1)); echo "  PASS  perl tier: riga scritta, telemetry_degraded NON emesso"
else
  FAIL=$((FAIL+1)); echo "  FAIL  perl tier (line_ok=$line_ok deg=$deg sentinel=$([ -f "$T1/.claude/.devforge-no-fsync-warned" ] && echo Y || echo N))"
fi
rm -rf "$T1"

# --- Caso 2: anche perl mascherato -> bash+sync, sync invocato + telemetry_degraded ---
T2="$(mktemp -d)"; mkdir -p "$T2/.claude/sess"
make_mask "$T2/bin" python python3 node perl
# shim sync che lascia un marker
cat > "$T2/bin/sync" <<EOF
#!/usr/bin/env bash
touch "$T2/.sync-called"
EOF
chmod +x "$T2/bin/sync"
run_append "$T2" "$T2/bin"
line_ok=$([ -s "$T2/.claude/target.jsonl" ] && echo 1 || echo 0)
deg=$(grep -c 'telemetry_degraded' "$T2/.claude/devforge-activity.jsonl" 2>/dev/null || true); deg="${deg//[!0-9]/}"; deg="${deg:-0}"
if [ "$line_ok" = "1" ] && [ -f "$T2/.sync-called" ] && [ "$deg" -ge 1 ]; then
  PASS=$((PASS+1)); echo "  PASS  ultima spiaggia: bash+sync invocato + telemetry_degraded emesso"
else
  FAIL=$((FAIL+1)); echo "  FAIL  ultima spiaggia (line_ok=$line_ok sync=$([ -f "$T2/.sync-called" ] && echo Y || echo N) deg=$deg)"
fi
rm -rf "$T2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui → DEVE fallire il Caso 1 (oggi python3+node mascherati → bash, emette telemetry_degraded).

### GREEN — implementa in lib/logger.sh

Nel blocco `_devforge_lock_append` (righe 162-184), rinomina `_node_ok` → `_fsync_ok`, aggiungi il tier perl tra node e bash, e aggiungi `sync` nel path bash. Sostituisci:

```bash
    local _node_ok=0
    if command -v node >/dev/null 2>&1; then
        # node: O_APPEND + fsyncSync via atomic_append.js
        if printf '%s' "$line" | node "${DEVFORGE_LIB_DIR}/atomic_append.js" "$file" 2>/dev/null; then
            _node_ok=1
        fi
    fi
    if [ "$_node_ok" -eq 0 ]; then
        # bash degraded: node absent OR node present-but-failed (no fsync, but never silent loss)
        printf '%s' "$line" >> "$file" 2>/dev/null
```

con:

```bash
    local _fsync_ok=0
    if command -v node >/dev/null 2>&1; then
        # node: O_APPEND + fsyncSync via atomic_append.js
        if printf '%s' "$line" | node "${DEVFORGE_LIB_DIR}/atomic_append.js" "$file" 2>/dev/null; then
            _fsync_ok=1
        fi
    fi
    if [ "$_fsync_ok" -eq 0 ] && command -v perl >/dev/null 2>&1; then
        # perl: append + IO::Handle::sync (fsync per-file reale) — elimina la degradazione no-fsync
        if printf '%s' "$line" | perl -e 'use IO::Handle; open(my $fh,">>",$ARGV[0]) or exit 1; local $/; my $d=<STDIN>; print $fh $d or exit 1; $fh->flush or exit 1; $fh->sync or exit 1; close($fh) or exit 1; exit 0' "$file" 2>/dev/null; then
            _fsync_ok=1
        fi
    fi
    if [ "$_fsync_ok" -eq 0 ]; then
        # ultima spiaggia (no python3+node+perl): bash + sync coarse (best-effort) + telemetry_degraded
        printf '%s' "$line" >> "$file" 2>/dev/null
        sync 2>/dev/null || true
```

(il resto del blocco — sentinel + telemetry_degraded + `rmdir` — resta invariato).

Aggiungi `sync` anche nel best-effort timeout (riga 146):
```bash
            printf '%s' "$line" >> "$file" 2>/dev/null
            sync 2>/dev/null || true
            return 0
```

Riesegui test → Caso 1 e Caso 2 PASS.

### Aggiorna T3b/T9b (gate bloccante)

In `tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh`, i test T3 (riga ~224) e T9b (riga ~409) usano la funzione `make_shim` (crea uno shim che esce 127) per mascherare python3 e node, e si aspettano `telemetry_degraded`. Ora quel path usa perl → l'evento non sarebbe emesso. **Edit concreto:** in **entrambe** le sezioni, subito **dopo** la riga `make_shim node` (sezione T3 intorno a riga 227; sezione T9b intorno a riga 411-412), aggiungi una riga identica per perl:
```bash
make_shim perl
```
`make_shim` ha la stessa firma delle chiamate esistenti (`make_shim python3`, `make_shim node`). Con perl mascherato a 127, il path raggiunge l'ultima spiaggia bash+sync e `telemetry_degraded` viene emesso come i test si aspettano. Leggi il file per confermare il nome esatto della funzione e i punti prima di editare (NON assumere: se la funzione si chiama diversamente, allinea).

### REFACTOR
Nessuno previsto: rinomina variabile + 2 blocchi additivi.

## Criteri di completamento
- [ ] `test_logger_perl_fsync.sh` PASS=2 FAIL=0
- [ ] Caso 1: perl tier durabile, no telemetry_degraded
- [ ] Caso 2: bash+sync, sync invocato + telemetry_degraded
- [ ] T3b/T9b aggiornati (mascherano anche perl) e verdi
- [ ] Suite zero-loss completa verde (tier python3/node invariati)
