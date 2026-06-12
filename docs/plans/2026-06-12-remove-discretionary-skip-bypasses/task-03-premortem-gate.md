# Task 03 — Rimuovi `DEVFORGE_SKIP_PREMORTEM` da pr-premortem-gate

**Goal:** Il gate premortem blocca anche con `DEVFORGE_SKIP_PREMORTEM=1`; branch di bypass e counter `.devforge-premortem-bypass-count` eliminati.

> Nota: questo bypass è emerso in spec-review, non era nell'inventario iniziale. È identico a SKIP_BLIND_REVIEW.

## File coinvolti
- Modifica: `hooks/pr-premortem-gate` (rimozione blocco righe 82-100)
- Modifica: `hooks/pr-premortem-gate` (ref nel messaggio `reason`, riga ~137)
- Verifica/crea test: cerca `tests/hooks/*premortem*`; se assente, aggiungi un caso al test del gate PR esistente o crea `tests/hooks/test_pr_premortem_gate.sh` sul modello di `test_pr_blind_review_gate.sh`.

## Step TDD

### Step 1 — Test
```bash
ls tests/hooks/ | grep -i premortem || echo "ASSENTE"
grep -rn "DEVFORGE_SKIP_PREMORTEM" tests/
```
Se esiste un test che asserisce allow con la var: invertilo. Se assente: crea `tests/hooks/test_pr_premortem_gate.sh` che pipe-a un envelope `PreToolUse` con `gh pr create` (senza evidenza siae-premortem nel ledger), setta `export DEVFORGE_SKIP_PREMORTEM=1`, e asserisce che l'output contiene `"decision":"block"`.

### Step 2 — Esegui e verifica che fallisce
```bash
bash tests/hooks/test_pr_premortem_gate.sh
```
Output atteso: FALLISCE (codice attuale ritorna `{}`).

### Step 3 — Rimuovi il branch di bypass
In `hooks/pr-premortem-gate` elimina interamente il blocco (righe 82-100):
```bash
# Explicit bypass with daily abuse tracking
if [ "${DEVFORGE_SKIP_PREMORTEM:-0}" = "1" ]; then
    BYPASS_FILE="${HOME}/.claude/.devforge-premortem-bypass-count"
    ...
    echo '{}'
    exit 0
fi
```
Lascia intatta la riga `devforge_init_session 2>/dev/null || true` (riga 80).

Nel messaggio `reason` (riga ~137), rimuovi la frase:
`Bypass tracciato (5/giorno): DEVFORGE_SKIP_PREMORTEM=1 <comando> (solo hotfix/bump/revert).`

### Step 4 — Esegui e verifica che passa
```bash
bash tests/hooks/test_pr_premortem_gate.sh
grep -n "DEVFORGE_SKIP_PREMORTEM" hooks/pr-premortem-gate
```
Output atteso: test PASS; nessun match per la var.

### Step 5 — Commit
```bash
git add hooks/pr-premortem-gate tests/hooks/
git commit -m "feat(hooks): rimuovi bypass discrezionale SKIP_PREMORTEM"
```

## Criteri di accettazione
- [ ] Nessun match per `DEVFORGE_SKIP_PREMORTEM` in `hooks/pr-premortem-gate`.
- [ ] Counter `.devforge-premortem-bypass-count` non più scritto.
- [ ] `reason` non cita più la var.
- [ ] Test del premortem gate PASS → gate blocca con var settata.
