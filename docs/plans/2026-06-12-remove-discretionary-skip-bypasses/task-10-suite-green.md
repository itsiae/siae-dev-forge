# Task 10 — Suite completa verde (verification gate finale)

**Goal:** L'intera suite `tests/run-all.sh` è verde dopo tutte le rimozioni, senza regressioni e senza chiamate di rete bloccanti. È il gate finale del piano.

> Dipendenza: dopo TUTTI i task 1-9.

## File coinvolti
- Nessuna modifica funzionale attesa (solo eventuali fix di regressione emersi).

## Step

### Step 1 — Esegui l'intera suite
```bash
bash tests/run-all.sh
```
Output atteso: tutti i test PASS. Cattura il conteggio finale (es. `N/N PASS`).

### Step 2 — Grep finale di assenza bypass discrezionali
```bash
grep -rn "DEVFORGE_SKIP_BRAINSTORMING\|DEVFORGE_SKIP_BLIND_REVIEW\|DEVFORGE_SKIP_RETRO_GATE\|DEVFORGE_SKIP_GIT_GATE\|DEVFORGE_FORCE_STOP\|DEVFORGE_SKIP_PREMORTEM\|DEVFORGE_SKIP_UPDATE\|DEVFORGE_SKIP_TRAILER_HOOK" hooks/ lib/
grep -rn "DEVFORGE_SKIP_EVIDENCE" hooks/
grep -rn "\.bypass-evidence\|\.devforge-skip-evidence" hooks/
```
Output atteso: **nessun match** nei file funzionali (i match residui possono esistere solo in `docs/plans/`, `CHANGELOG.md` storico, e nei test che asseriscono il block — NON in branch attivi degli hook).

### Step 3 — Verifica preservazione kill-switch (regression guard)
```bash
grep -rln "DEVFORGE_ENFORCEMENT_OFF\|DEVFORGE_USE_SESSION_SCOPE\|DEVFORGE_RELEASE_RISK_DISABLED\|DEVFORGE_BREAK_GLASS_REGEX" hooks/ lib/
```
Output atteso: i kill-switch globali/admin sono ANCORA presenti (non rimossi per errore).

### Step 4 — Syntax check di tutti gli hook modificati
```bash
for h in brainstorming-gate pr-blind-review-gate pr-premortem-gate pre-commit stop-gate review-evidence session-start; do bash -n "hooks/$h" && echo "OK $h"; done
bash -n lib/install-trailer-hook.sh && echo "OK trailer"
```
Output atteso: `OK` per ogni file, nessun errore di sintassi.

### Step 5 — Verdetto + commit (se servono fix)
Se la suite è verde e i grep confermano: il piano è completo. Se emergono fix di regressione, applicali (max 2 tentativi per errore, poi diagnosi diversa) e ri-esegui dallo Step 1.
```bash
# solo se sono stati applicati fix di regressione — elenca i file specifici
git add hooks/<file-corretto> tests/<file-corretto>
git commit -m "test: fix regressioni post-rimozione bypass discrezionali"
```

## Criteri di accettazione
- [ ] `tests/run-all.sh` interamente PASS (conteggio finale catturato).
- [ ] Zero match delle 9 var di skip discrezionale + `DEVFORGE_SKIP_EVIDENCE` + 2 state-file nei branch attivi di `hooks/` e `lib/`.
- [ ] Kill-switch globali/admin preservati (verificato).
- [ ] `bash -n` ok su tutti gli hook modificati.
