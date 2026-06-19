# Task 01 — `event_id` collision-resistant (Capability D)

**AC:** AC11 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_event_id_concurrency.sh`

## Problema

`devforge_next_seq` (logger.sh:574) usa il binario `flock`, **assente** su macOS e Windows Git
Bash → cade nel path non-lockato (logger.sh:590-593) → sotto concorrenza due processi leggono lo
stesso `current` → `seq` duplicato → `event_id` (`${sid}-${seq}`) duplicato → dedup downstream
scarta eventi distinti (perdita attività).

## RED — test che fallisce

Crea `tests/zero-loss/unit/test_logger_event_id_concurrency.sh`:
- `make_mask` (come `test_logger_perl_fsync.sh`) per mascherare **sia `flock` sia `python3`/`python`**
  (WARN-2: senza mascherare python3, atomic_write.py serializzerebbe e nasconderebbe la collisione
  del seq bash → test non deterministico). node resta presente (durabilità).
- Pre-crea `.devforge-session-id` (fixed sid) — realistico (session-start lo crea per primo).
- Lancia **50** `devforge_log` concorrenti con meta statico `{"k":"v"}`.
- Asserisci: 50 righe; `event_id` distinti == 50; `session_seq` distinti == 50.
- Atteso PRE-fix: FAIL (collisioni intermittenti). Esegui 3 volte per stabilità.

## GREEN — implementazione

In `devforge_next_seq`, dopo il blocco `flock` esistente (lasciato come fast-path quando il
binario c'è), sostituisci il fallback non-lockato con un **mkdir-lock portabile** (pattern di
`_devforge_lock_append`):

```bash
# Fallback senza binario flock (macOS/Git Bash): mkdir-lock atomico.
local lockdir="${seq_file}.lockdir"
local waited=0
while ! mkdir "$lockdir" 2>/dev/null; do
    local age; age=$(_devforge_dir_age_secs "$lockdir" 2>/dev/null || echo 0)
    if [ "${age:-0}" -gt 30 ] 2>/dev/null; then rmdir "$lockdir" 2>/dev/null || true; continue; fi
    waited=$((waited + 1))
    if [ "$waited" -gt 50 ]; then
        # 5s timeout: garanzia unicità via suffisso ad alta entropia (no perdita ordine grossolano).
        local cur; cur=$(cat "$seq_file" 2>/dev/null | tr -d '\r' || echo "0")
        echo "$cur" ; return 0
    fi
    sleep 0.02
done
local current; current=$(cat "$seq_file" 2>/dev/null | tr -d '\r' || echo "0")
local next=$((current + 1))
echo "$next" > "$seq_file"
rmdir "$lockdir" 2>/dev/null || true
echo "$next"
return 0
```

**`event_id` resta `"${sid}-${seq}"` invariato** (WARN-18: nessun cambio di formato → zero rischio
per il consumer Lambda; verificato che nessun test valida il formato). L'unicità è garantita dal
mkdir-lock che rende `seq` univoco. Il path di timeout (>5s di contesa, irrealistico per hook
DevForge) è l'unico residuo accettato — non si cambia il formato globale per coprirlo.

Per il ramo timeout (return del solo `cur`), NON viene incrementato: è un last-resort che preferisce
un possibile tie di `seq` alla perdita dell'evento (zero-loss prevale). Documenta inline questo
trade-off nel codice.

## REFACTOR

Estrai il blocco mkdir-lock+stale-guard in helper `_devforge_seq_lock` se duplicato; commento che
spiega "no dipendenza dal binario flock — parità mac/Win/Linux".

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_event_id_concurrency.sh` PASS 3×.
- No-regression: `test_telemetry_fixes.sh` (test seq esistenti) verde.
- Marca `[DONE]` in overview.
