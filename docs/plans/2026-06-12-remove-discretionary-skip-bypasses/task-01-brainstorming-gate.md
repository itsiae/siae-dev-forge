# Task 01 — Rimuovi `DEVFORGE_SKIP_BRAINSTORMING` da brainstorming-gate

**Goal:** Il gate brainstorming blocca anche con `DEVFORGE_SKIP_BRAINSTORMING=1`; il branch di bypass e il counter `.devforge-bypass-count` sono eliminati.

## File coinvolti
- Modifica: `hooks/brainstorming-gate` (rimozione blocco righe 109-136)
- Modifica: `hooks/brainstorming-gate` (riferimenti alla var nei messaggi `reason`, righe ~186 e ~195)
- Modifica/verifica test: `tests/hooks/brainstorming-gate.test.sh`

## Step TDD

### Step 1 — Inverti il test (test-first)
In `tests/hooks/brainstorming-gate.test.sh` individua il test che asserisce che con `DEVFORGE_SKIP_BRAINSTORMING=1` il gate ritorna `{}` (allow). Trasformalo in un test che asserisce che il gate **continua a bloccare/nudge** ignorando la var.

Comando per trovarlo:
```bash
grep -n "DEVFORGE_SKIP_BRAINSTORMING" tests/hooks/brainstorming-gate.test.sh
```
Asserzione target: dopo aver settato `export DEVFORGE_SKIP_BRAINSTORMING=1` e simulato il 4° edit senza brainstorming, l'output NON deve essere `{}` ma deve contenere `"decision": "block"` (o il nudge atteso allo stesso conteggio).

### Step 2 — Esegui e verifica che fallisce
```bash
bash tests/hooks/brainstorming-gate.test.sh
```
Output atteso: il test invertito FALLISCE (il codice attuale onora ancora la var → ritorna `{}`).

### Step 3 — Rimuovi il branch di bypass
In `hooks/brainstorming-gate`, elimina interamente il blocco (righe 109-136):
```bash
# Explicit bypass with daily abuse tracking (unchanged from PR #1)
if [ "${DEVFORGE_SKIP_BRAINSTORMING:-0}" = "1" ]; then
    SAFE_FILE_PATH=$(devforge_sanitize_json_str "$FILE_PATH")
    BYPASS_FILE="${HOME}/.claude/.devforge-bypass-count"
    ...
    echo '{}'
    exit 0
fi
```
Rimuovi anche, nei messaggi `reason`:
- riga ~186: l'opzione `(3) Fix triviale? Usa: DEVFORGE_SKIP_BRAINSTORMING=1 <comando>.` → riformula il nudge a 2 opzioni (invoca brainstorming / continua fino all'hard block).
- riga ~195: la frase `Bypass emergenza tracciato: DEVFORGE_SKIP_BRAINSTORMING=1 <comando>.` → rimuovila; lascia il puntamento a `#devforge-support` per i casi inappropriati.

### Step 4 — Esegui e verifica che passa
```bash
bash tests/hooks/brainstorming-gate.test.sh
```
Output atteso: tutti i test PASS (incluso quello invertito).

Verifica assenza residui:
```bash
grep -n "DEVFORGE_SKIP_BRAINSTORMING" hooks/brainstorming-gate
```
Output atteso: nessun match.

### Step 5 — Commit
```bash
git add hooks/brainstorming-gate tests/hooks/brainstorming-gate.test.sh
git commit -m "feat(hooks): rimuovi bypass discrezionale SKIP_BRAINSTORMING"
```

## Criteri di accettazione
- [ ] Nessun match per `DEVFORGE_SKIP_BRAINSTORMING` in `hooks/brainstorming-gate`.
- [ ] Nessuna scrittura su `.devforge-bypass-count` (variabile `BYPASS_FILE` rimossa, nessun orfano).
- [ ] I messaggi `reason` non citano più la var.
- [ ] `tests/hooks/brainstorming-gate.test.sh` PASS con la var settata → gate blocca/nudge.
