# Task 04 — Rimuovi `DEVFORGE_SKIP_GIT_GATE` da pre-commit

**Goal:** Il pre-commit gate blocca anche con `DEVFORGE_SKIP_GIT_GATE=1`; branch di bypass e counter `.devforge-git-gate-bypass-count` eliminati. **Attenzione:** il bypass è il ramo `if` di una catena `if/elif` — va ricondotto a `if`.

## File coinvolti
- Modifica: `hooks/pre-commit` (catena if/elif righe 108-131)
- Modifica: `hooks/pre-commit` (ref nel messaggio `reason`, riga ~142)
- Modifica/verifica test: `tests/test_hooks_compound_cmd.py` e/o test pre-commit dedicato.

## Step TDD

### Step 1 — Inverti/aggiungi il test
```bash
grep -rn "DEVFORGE_SKIP_GIT_GATE" tests/
```
Inverti il test che asserisce allow con la var in uno che asserisce `"decision":"block"` su `git commit` senza siae-git-workflow nel ledger, anche con `export DEVFORGE_SKIP_GIT_GATE=1`.

### Step 2 — Esegui e verifica che fallisce
```bash
python3 -m pytest tests/test_hooks_compound_cmd.py -v   # se il caso è qui
# oppure il test bash pertinente
```
Output atteso: il test invertito FALLISCE.

### Step 3 — Rimuovi il ramo di bypass e ricostruisci la catena
In `hooks/pre-commit` la struttura attuale (righe 108-131) è:
```bash
if [ "$IS_GIT_COMMIT" = "1" ]; then
    if [ "${DEVFORGE_SKIP_GIT_GATE:-0}" = "1" ]; then
        BYPASS_FILE="${HOME}/.claude/.devforge-git-gate-bypass-count"
        ...
        # Bypass branch: no block, no early exit.
    # Check if siae-git-workflow was invoked this session — HARD GATE
    elif ! echo "$SESSION_SKILLS" | grep -qF "siae-git-workflow"; then
        ...
```
Rimuovi l'intero ramo `if [ "${DEVFORGE_SKIP_GIT_GATE:-0}" = "1" ]; then ... ` (incluso il commento sul bypass branch) e converti `elif !` in `if !`. Risultato atteso:
```bash
if [ "$IS_GIT_COMMIT" = "1" ]; then
    # Check if siae-git-workflow was invoked this session — HARD GATE
    if ! echo "$SESSION_SKILLS" | grep -qF "siae-git-workflow"; then
        ...
```
Aggiorna anche il commento alle righe 109-111 che spiega il bypass d'emergenza (rimuovilo o riformulalo: il gate non ha più bypass).

Nel messaggio `reason` (riga ~142), rimuovi:
`\n\nEmergency bypass (tracked): DEVFORGE_SKIP_GIT_GATE=1 git commit ...`

### Step 4 — Esegui e verifica che passa
```bash
python3 -m pytest tests/test_hooks_compound_cmd.py -v
bash -n hooks/pre-commit   # syntax check: nessun errore di sintassi dopo la ristrutturazione
grep -n "DEVFORGE_SKIP_GIT_GATE" hooks/pre-commit
```
Output atteso: test PASS; `bash -n` senza errori; nessun match per la var.

### Step 5 — Commit
```bash
git add hooks/pre-commit tests/
git commit -m "feat(hooks): rimuovi bypass discrezionale SKIP_GIT_GATE"
```

## Criteri di accettazione
- [ ] Nessun match per `DEVFORGE_SKIP_GIT_GATE` in `hooks/pre-commit`.
- [ ] La catena `if/elif` è correttamente ridotta a `if` (verificato con `bash -n`).
- [ ] Counter `.devforge-git-gate-bypass-count` non più scritto.
- [ ] `reason` non cita più la var.
- [ ] Test pre-commit PASS → gate blocca con var settata.
