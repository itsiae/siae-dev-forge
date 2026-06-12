# Task 05 — Rimuovi `DEVFORGE_SKIP_RETRO_GATE` + `DEVFORGE_FORCE_STOP` da stop-gate

**Goal:** Lo stop-gate (retrospective + verification) blocca anche con `DEVFORGE_SKIP_RETRO_GATE=1` o `DEVFORGE_FORCE_STOP=1`; entrambi i branch e il counter `.devforge-force-stop-count` eliminati.

## File coinvolti
- Modifica: `hooks/stop-gate` (branch retro righe 190-194; branch force-stop righe 252-270; commenti 187 e 217; reason 284)
- Modifica/verifica test: cerca i test stop-gate.

## Step TDD

### Step 1 — Inverti/aggiungi i test
```bash
grep -rn "DEVFORGE_SKIP_RETRO_GATE\|DEVFORGE_FORCE_STOP" tests/
```
Inverti (o aggiungi) due test:
1. Sessione produttiva senza siae-retrospective + `export DEVFORGE_SKIP_RETRO_GATE=1` → output `"decision": "block"` (non più `exit 0`).
2. Claim di completamento senza siae-verification + `export DEVFORGE_FORCE_STOP=1` → output `"decision": "block"`.

### Step 2 — Esegui e verifica che falliscono
Il test stop-gate è `tests/hooks/test_evidence_stop_gate.sh`. Verifica con:
```bash
grep -rn "DEVFORGE_SKIP_RETRO_GATE\|DEVFORGE_FORCE_STOP" tests/
bash tests/hooks/test_evidence_stop_gate.sh
```
Output atteso: entrambi i test invertiti FALLISCONO (il codice attuale onora ancora le var → `exit 0`).

### Step 3 — Rimuovi i due branch di bypass
**Branch retrospective (righe 190-194):** dentro `if ! echo "$SKILLS_LIST" | grep -qF "siae-retrospective"; then` rimuovi:
```bash
        if [ "${DEVFORGE_SKIP_RETRO_GATE:-0}" = "1" ]; then
            devforge_log "stop_gate" "skipped_retro" "{...}"
            _devforge_emit_session_end
            exit 0
        fi
```
Lasciando il `devforge_log ... blocked_retro` e il blocco `RETRO_EOF` che seguono.

**Branch force-stop (righe 252-270):** rimuovi interamente:
```bash
# Explicit bypass — DEVFORGE_FORCE_STOP=1 (tracked, daily abuse counter)
if [ "${DEVFORGE_FORCE_STOP:-0}" = "1" ]; then
    FORCE_COUNT_FILE="${HOME}/.claude/.devforge-force-stop-count"
    ...
    _devforge_emit_session_end
    exit 0
fi
```
Lasciando intatto il blocco `# Hard block — no auto-escape.` che segue (riga 272+).

**Commenti:** aggiorna riga 187 (`Ambienti non interattivi ... possono bypassare via: DEVFORGE_SKIP_RETRO_GATE=1`) e riga 217 (`DEVFORGE_FORCE_STOP=1 <command>`) rimuovendo i riferimenti alle var.

**Reason (riga 284):** rimuovi `Escape esplicito (tracciato 3/giorno): DEVFORGE_FORCE_STOP=1 <comando>.`

### Step 4 — Esegui e verifica che passano
```bash
bash -n hooks/stop-gate
grep -n "DEVFORGE_SKIP_RETRO_GATE\|DEVFORGE_FORCE_STOP" hooks/stop-gate
bash tests/hooks/test_evidence_stop_gate.sh
```
Output atteso: `bash -n` senza errori; nessun match per le var; test PASS.

### Step 5 — Commit
```bash
git add hooks/stop-gate tests/
git commit -m "feat(hooks): rimuovi bypass SKIP_RETRO_GATE e FORCE_STOP da stop-gate"
```

## Criteri di accettazione
- [ ] Nessun match per `DEVFORGE_SKIP_RETRO_GATE` né `DEVFORGE_FORCE_STOP` in `hooks/stop-gate`.
- [ ] Counter `.devforge-force-stop-count` non più scritto.
- [ ] `bash -n hooks/stop-gate` senza errori.
- [ ] Commenti e `reason` non citano più le var.
- [ ] Test stop-gate PASS → blocca con le var settate.
