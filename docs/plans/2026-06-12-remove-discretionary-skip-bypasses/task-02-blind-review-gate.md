# Task 02 — Rimuovi `DEVFORGE_SKIP_BLIND_REVIEW` da pr-blind-review-gate

**Goal:** Il gate blind-review blocca anche con `DEVFORGE_SKIP_BLIND_REVIEW=1`; branch di bypass e counter `.devforge-blind-review-bypass-count` eliminati.

## File coinvolti
- Modifica: `hooks/pr-blind-review-gate` (rimozione blocco righe 84-102)
- Modifica: `hooks/pr-blind-review-gate` (ref nel messaggio `reason`, riga ~139)
- Modifica/verifica test: `tests/hooks/test_pr_blind_review_gate.sh`

## Step TDD

### Step 1 — Inverti il test
```bash
grep -n "DEVFORGE_SKIP_BLIND_REVIEW" tests/hooks/test_pr_blind_review_gate.sh
```
Trasforma il test che asserisce allow (`{}`) con la var settata in uno che asserisce `"decision":"block"` su `gh pr create` senza evidenza blind-review, anche con `export DEVFORGE_SKIP_BLIND_REVIEW=1`.

### Step 2 — Esegui e verifica che fallisce
```bash
bash tests/hooks/test_pr_blind_review_gate.sh
```
Output atteso: il test invertito FALLISCE (codice attuale ritorna `{}`).

### Step 3 — Rimuovi il branch di bypass
In `hooks/pr-blind-review-gate` elimina interamente il blocco (righe 84-102):
```bash
# Explicit bypass with daily abuse tracking
if [ "${DEVFORGE_SKIP_BLIND_REVIEW:-0}" = "1" ]; then
    BYPASS_FILE="${HOME}/.claude/.devforge-blind-review-bypass-count"
    ...
    echo '{}'
    exit 0
fi
```
Lascia intatta la riga `devforge_init_session 2>/dev/null || true` (riga 82) che precede il blocco.

Nel messaggio `reason` (riga ~139), rimuovi la frase:
`Bypass tracked (5/giorno): DEVFORGE_SKIP_BLIND_REVIEW=1 <comando>.`

### Step 4 — Esegui e verifica che passa
```bash
bash tests/hooks/test_pr_blind_review_gate.sh
grep -n "DEVFORGE_SKIP_BLIND_REVIEW" hooks/pr-blind-review-gate
```
Output atteso: test PASS; nessun match per la var.

### Step 5 — Commit
```bash
git add hooks/pr-blind-review-gate tests/hooks/test_pr_blind_review_gate.sh
git commit -m "feat(hooks): rimuovi bypass discrezionale SKIP_BLIND_REVIEW"
```

## Criteri di accettazione
- [ ] Nessun match per `DEVFORGE_SKIP_BLIND_REVIEW` in `hooks/pr-blind-review-gate`.
- [ ] Counter `.devforge-blind-review-bypass-count` non più scritto.
- [ ] `reason` non cita più la var.
- [ ] `tests/hooks/test_pr_blind_review_gate.sh` PASS → gate blocca con var settata.
