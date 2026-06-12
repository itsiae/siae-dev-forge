# Task 08 — Rimuovi `SKIP_UPDATE` (+ timeout) e `SKIP_TRAILER_HOOK`

**Goal:** Rimuovere i 2 skip non-gate: `DEVFORGE_SKIP_UPDATE` (session-start auto-update) con guard timeout portabile al posto dello skip, e `DEVFORGE_SKIP_TRAILER_HOOK` (opt-out install trailer). Pulire le 7 occorrenze in `run-all.sh`.

## File coinvolti
- Modifica: `hooks/session-start` (riga 146 + chiamata `gh release list` riga 147)
- Modifica: `lib/install-trailer-hook.sh` (commento riga 9, check riga 14)
- Modifica: `tests/run-all.sh` (7 occorrenze `DEVFORGE_SKIP_UPDATE=1`, righe 799, 980, 991, 1016, 1029, 1040, 1056)

## Step TDD

### Step 1 — Test
Aggiungi/adatta un test che invoca `bash hooks/session-start` SENZA env var di skip e verifica che termini rapidamente e produca JSON valido anche offline (la chiamata `gh release list` deve fallire-fast via timeout, non hang). Per il trailer: verifica che `install-trailer-hook.sh` installi l'hook anche senza `DEVFORGE_SKIP_TRAILER_HOOK` (e che resti zero-harm sui repo con `prepare-commit-msg` estraneo).
```bash
grep -rn "DEVFORGE_SKIP_TRAILER_HOOK" tests/
```

### Step 2 — Esegui e verifica baseline
```bash
bash tests/run-all.sh 2>&1 | tail -20   # baseline pre-modifica
```

### Step 3a — session-start: rimuovi SKIP_UPDATE + timeout guard
In `hooks/session-start` riga 146, sostituisci il guard:
```bash
if command -v gh >/dev/null 2>&1 && [ "$PLUGIN_VERSION" != "unknown" ] && [ "${DEVFORGE_SKIP_UPDATE:-}" != "1" ]; then
```
con (rimosso lo skip):
```bash
if command -v gh >/dev/null 2>&1 && [ "$PLUGIN_VERSION" != "unknown" ]; then
```
Aggiungi un wrapper timeout portabile alla chiamata `gh release list` (riga 147) per fail-fast offline (pattern memory `feedback_macos_timeout_portability`). Definisci vicino all'inizio un helper o inline:
```bash
    if command -v timeout >/dev/null 2>&1; then
        LATEST_TAG=$(timeout 5 gh release list --repo itsiae/siae-dev-forge --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null || echo "")
    else
        LATEST_TAG=$(gh release list --repo itsiae/siae-dev-forge --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null || echo "")
    fi
```

### Step 3b — install-trailer-hook: rimuovi SKIP_TRAILER_HOOK
In `lib/install-trailer-hook.sh`:
- riga 14: rimuovi `[ "${DEVFORGE_SKIP_TRAILER_HOOK:-}" = "1" ] && return 0`
- riga 9: aggiorna il commento `Opt-out: DEVFORGE_SKIP_TRAILER_HOOK=1.` → indica che per saltare un singolo commit si usa `git commit --no-verify`.

### Step 3c — run-all.sh: rimuovi il prefisso
Rimuovi `DEVFORGE_SKIP_UPDATE=1 ` (prefisso) dalle 7 invocazioni di `session-start` in `tests/run-all.sh` (righe 799, 980, 991, 1016, 1029, 1040, 1056). Mantieni il resto della riga invariato (es. `HOME="${TEST_TMP}" bash ... session-start`).

### Step 4 — Esegui e verifica
```bash
bash -n hooks/session-start lib/install-trailer-hook.sh
grep -rn "DEVFORGE_SKIP_UPDATE\|DEVFORGE_SKIP_TRAILER_HOOK" hooks/ lib/ tests/run-all.sh
bash tests/run-all.sh 2>&1 | tail -20
```
Output atteso: `bash -n` ok; nessun match per le due var; `run-all.sh` verde senza hang di rete (il timeout taglia la chiamata gh offline).

### Step 5 — Commit
```bash
git add hooks/session-start lib/install-trailer-hook.sh tests/run-all.sh tests/
git commit -m "feat(hooks): rimuovi SKIP_UPDATE (timeout guard) e SKIP_TRAILER_HOOK"
```

## Criteri di accettazione
- [ ] Nessun match `DEVFORGE_SKIP_UPDATE` in `hooks/session-start` né in `tests/run-all.sh`.
- [ ] `gh release list` ha timeout portabile (fail-fast offline, no hang).
- [ ] Nessun match `DEVFORGE_SKIP_TRAILER_HOOK` in `lib/install-trailer-hook.sh`.
- [ ] `run-all.sh` verde; session-start produce JSON valido anche offline.
