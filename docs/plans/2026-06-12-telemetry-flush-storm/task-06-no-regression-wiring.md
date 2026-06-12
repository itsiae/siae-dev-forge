# Task 06 — Wiring GC + no-regression (cooldown invariato, suite verde)

**Goal:** Cablare `devforge_gc_maybe` nel ciclo di upload, verificare che il cooldown 60s del flusher resti invariato, lo zero-loss sia preservato (nessun batch sparito su upload fallito), e che la suite telemetria esistente resti verde.

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (funzione `devforge_upload_logs`)
- Modifica: `tests/test_telemetry_flush_storm.sh` (aggiungi test 13-14)
- Esegui (no modifica): `tests/test_telemetry_fixes.sh`, suite `tests/zero-loss/`

## Step TDD bite-sized

### Step 1 — Scrivi i test fallenti

Aggiungi in `tests/test_telemetry_flush_storm.sh` prima del blocco `Totale:`:

```bash
# ── Test 13: devforge_upload_logs invokes GC (wiring) ──
echo "Test 13: upload_logs triggers gc_maybe"
new_env
export DEVFORGE_SID="sess-CURRENT"
# Stub the heavy bits so we isolate the GC wiring
devforge_create_batch() { :; }
devforge_batch_global() { :; }
devforge_upload_backlog() { :; }
_GC_CALLED=0
devforge_gc_maybe() { _GC_CALLED=1; }
devforge_upload_logs
assert_eq "upload_logs calls gc_maybe" "1" "$_GC_CALLED"
unset DEVFORGE_SID
cleanup_env
# Re-source to restore real functions after stubbing
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh"

# ── Test 14: zero-loss — failed upload never deletes a batch ──
echo "Test 14: zero-loss on failed upload"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=99   # never dead-letter within this test
ob=$(seed_outbox "sess-Z" 4)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog
total=$(( $(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ') + $([ -d "$ob/failed" ] && ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo 0) ))
assert_eq "no batch lost on failed upload" "4" "$total"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env
```

### Step 2 — Esegui e verifica che falliscono

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 13 FAIL (`upload_logs calls gc_maybe` → 0, GC non cablata).

### Step 3 — Cabla la GC in `devforge_upload_logs`

In `lib/telemetry-upload.sh`, modifica `devforge_upload_logs` (righe 125-129 attuali) aggiungendo la chiamata GC:

```bash
devforge_upload_logs() {
    devforge_create_batch 2>/dev/null || true
    devforge_batch_global 2>/dev/null || true
    devforge_upload_backlog 2>/dev/null || true
    devforge_gc_maybe 2>/dev/null || true
}
```

> La GC è dietro sentinel giornaliero (`devforge_gc_maybe`), quindi cablarla qui non aggiunge costo per-flush significativo: scatta una volta al giorno indipendentemente da quante volte `devforge_upload_logs` viene chiamata dai 7 call-site.

### Step 4 — Esegui e verifica che passano (test nuovi + suite esistente)

Run nuovi test:
`bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 13/14 PASS · `Totale: PASS=14 FAIL=0` (1+3+2+3+3+2 dai task 1-6).

Run suite esistente (no-regression):
`bash tests/test_telemetry_fixes.sh`
Output atteso: tutti PASS (cursor/canonicalize invariati), exit 0.

Run zero-loss suite:
`cd tests/zero-loss && make test` (o `python3 -m pytest tests/zero-loss -q` se Makefile assente)
Output atteso: nessun nuovo failure rispetto a baseline pre-modifica.

Verifica cooldown flusher invariato (strutturale):
`grep -n "COOLDOWN_SEC=60" hooks/devforge-flusher`
Output atteso: `25:COOLDOWN_SEC=60` — il valore non è stato toccato.

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "feat(telemetry): cabla devforge_gc_maybe in upload_logs + test no-regression/zero-loss"
```

## Criteri di accettazione

- [ ] `devforge_upload_logs` chiama `devforge_gc_maybe` (dietro sentinel giornaliero).
- [ ] Test 13/14 PASS; `tests/test_telemetry_flush_storm.sh` → PASS=14 FAIL=0.
- [ ] `tests/test_telemetry_fixes.sh` resta verde (exit 0).
- [ ] Suite `tests/zero-loss/` senza nuovi failure.
- [ ] `COOLDOWN_SEC=60` invariato in `hooks/devforge-flusher`.
- [ ] Upload fallito (non-200) non cancella mai un batch: somma outbox+failed = N iniziali.
