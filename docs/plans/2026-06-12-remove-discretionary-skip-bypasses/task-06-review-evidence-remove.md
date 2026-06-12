# Task 06 — Rimuovi skip discrezionale da review-evidence

**Goal:** Rimuovere i 3 short-circuit discrezionali in `hooks/review-evidence` (state-file legacy `.devforge-skip-evidence`, session-marker `.bypass-evidence`, env var `DEVFORGE_SKIP_EVIDENCE`) e i riferimenti a `DEVFORGE_SKIP_EVIDENCE` nei messaggi di **verdetto qualità**. NON tocca ancora i path di tool-fail (Task 07).

> Dipendenza: precede Task 07 (stesso file). Eseguire 06 → 07 in ordine.

## File coinvolti
- Modifica: `hooks/review-evidence` (blocco righe 68-91; reason quality righe ~460 e ~500)
- Modifica/verifica test: `tests/test_review_evidence_hook.py`, `tests/test_forge_evidence_command.py`

## Step TDD

### Step 1 — Inverti i test
```bash
grep -n "DEVFORGE_SKIP_EVIDENCE\|bypass-evidence\|devforge-skip-evidence" tests/test_review_evidence_hook.py tests/test_forge_evidence_command.py
```
Inverti i test che asseriscono allow (`{}`) tramite:
- `export DEVFORGE_SKIP_EVIDENCE=1` su un trigger bloccante,
- presenza del file session-marker `.bypass-evidence`.

Nuova asserzione: su `BLOCK_REGRESSION` (o hard-block) con `DEVFORGE_SKIP_EVIDENCE=1` settata, l'output resta `"decision":"block"` (la var non è più onorata come skip discrezionale). NB: il breakglass tool-fail di Task 07 NON deve far passare un verdetto di qualità — aggiungi un test esplicito in Task 07.

> Se uno dei due file (`test_review_evidence_hook.py` / `test_forge_evidence_command.py`) **non** contiene un caso con `DEVFORGE_SKIP_EVIDENCE=1` su un trigger bloccante, **crea** il caso (non limitarti a invertire quelli esistenti) — così la regressione "la var non è più onorata" è coperta in entrambi.

### Step 2 — Esegui e verifica che falliscono
```bash
python3 -m pytest tests/test_review_evidence_hook.py -v
```
Output atteso: i test invertiti FALLISCONO (codice attuale onora la var/marker).

### Step 3 — Rimuovi i 3 short-circuit discrezionali
In `hooks/review-evidence` elimina l'intero blocco righe 68-91:
```bash
# Legacy global state file `~/.claude/.devforge-skip-evidence` auto-rimosso.
SKIP_STATE_FILE="${HOME}/.claude/.devforge-skip-evidence"
if [ -f "$SKIP_STATE_FILE" ]; then
    rm -f "$SKIP_STATE_FILE" 2>/dev/null || true
    devforge_log "evidence_bypass_legacy_removed" "warn" "{...}" 2>/dev/null || true
fi
# BUG A fix: session-scoped marker (subprocess-safe, session-end cleanup)
_DEVFORGE_SID=$(cat "${HOME}/.claude/.devforge-sid" 2>/dev/null || echo "")
if [ -n "$_DEVFORGE_SID" ]; then
    _BYPASS_FILE="${HOME}/.claude/devforge-state/${_DEVFORGE_SID}/.bypass-evidence"
    if [ -f "$_BYPASS_FILE" ]; then
        devforge_log "evidence_bypass_used" "info" "{...}" 2>/dev/null || true
        echo '{}'
        exit 0
    fi
fi
if [ "${DEVFORGE_SKIP_EVIDENCE:-0}" = "1" ]; then
    devforge_log "evidence_bypass_used" "info" "{...}" 2>/dev/null || true
    echo '{}'
    exit 0
fi
```
Il commento BUG A/BUG B sopra (righe 62-67) resta. La riga successiva al blocco rimosso (pre-check jq, attuale riga 93 `# ── E05: pre-check jq ...`) diventa il nuovo punto di continuazione.

### Step 4 — Rimuovi `DEVFORGE_SKIP_EVIDENCE` dai reason di verdetto qualità
Solo nei messaggi di **verdetto qualità** (NON i path tool-fail, gestiti in Task 07):
- riga ~460 (`BLOCK_REGRESSION` / review-evidence v2): rimuovi `Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass) (tracked, abuse 5/day).` → sostituisci con indicazione di risolvere via fix reale o `/forge-fix-evidence`.
- riga ~500 (hard-block): rimuovi `Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)`.

NON toccare le righe 102, 305, 351, 386, 398 (path tool-fail) in questo task.

### Step 5 — Esegui, verifica, commit
```bash
bash -n hooks/review-evidence
python3 -m pytest tests/test_review_evidence_hook.py tests/test_forge_evidence_command.py -v
grep -n "DEVFORGE_SKIP_EVIDENCE\|bypass-evidence\|devforge-skip-evidence" hooks/review-evidence
```
Output atteso: `bash -n` ok; test PASS; i match residui di `DEVFORGE_SKIP_EVIDENCE` sono SOLO nei 5 path tool-fail (102, 305, 351, 386, 398), che Task 07 trasformerà.
```bash
git add hooks/review-evidence tests/test_review_evidence_hook.py tests/test_forge_evidence_command.py
git commit -m "feat(hooks): rimuovi skip discrezionale evidence (env var + state-file)"
```

## Criteri di accettazione
- [ ] Nessun short-circuit discrezionale: rimossi blocco env var, session-marker e blocco legacy.
- [ ] I reason di `BLOCK_REGRESSION` e hard-block non citano più `DEVFORGE_SKIP_EVIDENCE` come override.
- [ ] `bash -n hooks/review-evidence` senza errori.
- [ ] Test PASS: `BLOCK_REGRESSION` con `DEVFORGE_SKIP_EVIDENCE=1` resta block.
- [ ] Residui `DEVFORGE_SKIP_EVIDENCE` solo nei 5 path tool-fail (input per Task 07).
