# Task 01: DEVFORGE_STATE_DIR + Bug Fix Plumbing (D1)

**Deliverable:** D1
**Dipendenze:** nessuna (primo task)
**File coinvolti:** `lib/logger.sh`, `hooks/post-skill`, `hooks/devforge-context-always`, `hooks/session-start`, `hooks/pre-commit`, `hooks/stop-gate`, `hooks/tdd-gate`, `hooks/plan-gate`, `hooks/sub-skill-gate`, `hooks/devforge-reinject`, `hooks/capture-test-result`, `tests/run-all.sh`

---

## Step 1 — Test: verifica che STATE_DIR non esiste ancora

```bash
grep -r 'DEVFORGE_STATE_DIR' lib/ hooks/ tests/
```
Output atteso: nessun match (conferma che la variabile non esiste).

## Step 2 — Aggiungi DEVFORGE_STATE_DIR in `lib/logger.sh`

Modifica: `lib/logger.sh`, subito dopo la riga `#!/usr/bin/env bash` e i commenti iniziali, **prima** di qualsiasi definizione di variabile che usa `${HOME}/.claude`:

```bash
# ─── State directory (centralizzata, overridable per test/CI) ───
DEVFORGE_STATE_DIR="${DEVFORGE_STATE_DIR:-${HOME}/.claude}"
```

Aggiorna nella stesso file tutte le occorrenze di `${HOME}/.claude` con `${DEVFORGE_STATE_DIR}`:
- `DEVFORGE_SID_FILE` (riga ~6)
- `DEVFORGE_LOG_FILE` default (riga ~7)

## Step 3 — Fix bug ALTO 2: sentinel CWD → STATE_DIR

In `lib/logger.sh`, funzione `devforge_set_mode()` (riga ~166):

```bash
# PRIMA (BUG):
echo "$context" > "$(pwd)/.devforge-active-${mode}"

# DOPO (FIX):
echo "$context" > "${DEVFORGE_STATE_DIR}/.devforge-active-${mode}"
```

Stessa modifica per `devforge_clear_mode()` (riga ~177):
```bash
# PRIMA:
rm -f "$(pwd)/.devforge-active-${mode}"

# DOPO:
rm -f "${DEVFORGE_STATE_DIR}/.devforge-active-${mode}"
```

## Step 4 — Fix bug ALTO 1: session-skills da CSV a una-skill-per-riga

In `hooks/post-skill` (righe 46-52), sostituire la logica CSV:

```bash
# PRIMA (BUG — scrive CSV su una riga):
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
EXISTING_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")
if [ -z "$EXISTING_SKILLS" ]; then
    echo "$SKILL_NAME" > "${SESSION_SKILLS_FILE}.tmp" && mv "${SESSION_SKILLS_FILE}.tmp" "$SESSION_SKILLS_FILE"
elif ! echo "$EXISTING_SKILLS" | grep -qF "$SKILL_NAME"; then
    echo "${EXISTING_SKILLS},${SKILL_NAME}" > "${SESSION_SKILLS_FILE}.tmp" && mv "${SESSION_SKILLS_FILE}.tmp" "$SESSION_SKILLS_FILE"
fi

# DOPO (FIX — una skill per riga, dedup con grep):
SESSION_SKILLS_FILE="${DEVFORGE_STATE_DIR}/.devforge-session-skills"
if [ ! -f "$SESSION_SKILLS_FILE" ] || ! grep -qxF "$SKILL_NAME" "$SESSION_SKILLS_FILE" 2>/dev/null; then
    echo "$SKILL_NAME" >> "$SESSION_SKILLS_FILE"
fi
```

## Step 5 — Fix bug MEDIO 3: output sporco con pipefail

In `hooks/devforge-context-always` (riga 77):

```bash
# PRIMA (BUG — grep -c fallisce con pipefail su file vuoto/assente):
SKILLS=$(cat "${STATE_DIR}/.devforge-session-skills" 2>/dev/null | grep -c '.' || echo "0")

# DOPO (FIX — wc -l su file one-skill-per-line):
SKILLS_FILE="${STATE_DIR}/.devforge-session-skills"
if [ -f "$SKILLS_FILE" ]; then
    SKILLS=$(wc -l < "$SKILLS_FILE" | tr -d ' ')
else
    SKILLS=0
fi
```

## Step 6 — Migra tutti gli hook a DEVFORGE_STATE_DIR

Per ogni hook che accede a `${HOME}/.claude/.devforge-*`, sostituisci con `${DEVFORGE_STATE_DIR}/.devforge-*`.

Hook che sourciano `lib/logger.sh` (ereditano automaticamente):
- `hooks/session-start` — sostituisci `${HOME}/.claude` con `${DEVFORGE_STATE_DIR}`
- `hooks/stop-gate` — idem
- `hooks/post-skill` — idem (gia' fatto in Step 4 per session-skills)
- `hooks/capture-test-result` — idem

Hook che NON sourciano logger.sh — aggiungere in cima:
- `hooks/devforge-context-always` — cambiare `STATE_DIR="${HOME}/.claude"` (riga 18) in `STATE_DIR="${DEVFORGE_STATE_DIR:-${HOME}/.claude}"`
- `hooks/devforge-reinject` — cambiare `COUNTER_FILE="${HOME}/.claude/.devforge-message-counter"` (riga 19) in `COUNTER_FILE="${DEVFORGE_STATE_DIR:-${HOME}/.claude}/.devforge-message-counter"`
- `hooks/pre-commit` — sostituisci path hardcoded
- `hooks/tdd-gate` — idem
- `hooks/plan-gate` — idem
- `hooks/sub-skill-gate` — idem

## Step 7 — Aggiorna riferimenti in tests/run-all.sh

Sostituisci ogni `${HOME}/.claude/.devforge-*` in `tests/run-all.sh` con `${DEVFORGE_STATE_DIR}/.devforge-*`.

## Step 8 — Aggiorna lettori di session-skills che usano il formato CSV

Cerca tutti i file che leggono `.devforge-session-skills` e trattano il contenuto come CSV (split su virgola). Aggiornali per leggere una-skill-per-riga:

```bash
grep -rn 'session-skills' hooks/ lib/ tests/
```

Per ogni match: se usa `grep -qF "$SKILL"` (check singola skill), funziona gia' con una-per-riga. Se splitta su virgola, aggiornare.

## Step 9 — Run test e verifica

```bash
DEVFORGE_STATE_DIR=/tmp/devforge-test-$$ tests/run-all.sh
```
Output atteso: tutti i test passano, nessun accesso a `~/.claude/`.

Verifica extra:
```bash
# Nessun hardcoded ${HOME}/.claude rimasto (escluso il default del fallback)
grep -rn '${HOME}/.claude' hooks/ lib/ | grep -v 'DEVFORGE_STATE_DIR:-'
```
Output atteso: zero match.

## Step 10 — Commit

```bash
git add lib/logger.sh hooks/post-skill hooks/devforge-context-always hooks/session-start \
  hooks/pre-commit hooks/stop-gate hooks/tdd-gate hooks/plan-gate hooks/sub-skill-gate \
  hooks/devforge-reinject hooks/capture-test-result tests/run-all.sh
git commit -m "refactor(state): centralize DEVFORGE_STATE_DIR + fix 3 plumbing bugs

- Add DEVFORGE_STATE_DIR to lib/logger.sh (default: ~/.claude)
- Fix sentinel written to CWD instead of STATE_DIR (bug ALTO 2)
- Fix session-skills CSV format → one-skill-per-line (bug ALTO 1)
- Fix dirty output skills=0\n0 with pipefail (bug MEDIO 3)
- Migrate all hooks and tests to use DEVFORGE_STATE_DIR

Co-Authored-By: SIAE DevForge"
```
