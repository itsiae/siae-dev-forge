# Task 07 — Generalizza `skills/siae-premortem/SKILL.md`

> **REQUIRED SUB-SKILL:** `siae-tdd` (test: grep + verifica struttura markdown)

**Goal:** SKILL.md `siae-premortem` non contiene più riferimenti `itsiae/*` nello scope. Sezione "Scope di attivazione" aggiunta con env var e state file documentati.

**File coinvolti:**
- Modifica: `skills/siae-premortem/SKILL.md` (3 edits)
- Crea: `tests/skill_premortem_generalized.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/skill_premortem_generalized.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="${REPO_ROOT}/skills/siae-premortem/SKILL.md"

PASS=0
FAIL=0

assert() {
    local desc="$1" cmd="$2"
    if eval "$cmd"; then
        PASS=$((PASS + 1)); printf "  [PASS] %s\n" "$desc"
    else
        FAIL=$((FAIL + 1)); printf "  [FAIL] %s\n" "$desc"
    fi
}

# Verifica zero scope coupling
assert "no 'on itsiae/* repos' in description" "! grep -q 'on itsiae/\* repos' '$SKILL'"
assert "no 'prima di gh pr create su itsiae' in body" "! grep -q 'prima di .gh pr create. su .itsiae' '$SKILL'"

# Verifica sezione Scope presente
assert "section 'Scope di attivazione' present" "grep -q '^## Scope di attivazione$' '$SKILL'"
assert "DEVFORGE_GATE_SCOPE documented" "grep -q 'DEVFORGE_GATE_SCOPE' '$SKILL'"
assert "state file documented" "grep -q '.devforge-gate-scope' '$SKILL'"
assert "ENV_VARS.md ref present" "grep -q 'hooks/ENV_VARS.md' '$SKILL'"

echo
echo "skill_premortem_generalized.test.sh — PASS: $PASS / 6 — FAIL: $FAIL / 6"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/skill_premortem_generalized.test.sh
```

Atteso: 4 FAIL (le 2 ref scope ci sono ancora, la sezione Scope non esiste). Exit 1.

## Step 3 — Implementa gli edit

### Edit 1 — L4 (description)

Sostituisci:
```
  Use BEFORE opening a Pull Request on itsiae/* repos. Applies Gary Klein's
```
Con:
```
  Use BEFORE opening a Pull Request. Applies Gary Klein's
```

### Edit 2 — L48

Sostituisci:
```
**Sempre, prima di `gh pr create` su `itsiae/*`.** Il hook `pr-premortem-gate` blocca la creazione PR se non c'e' evidenza di invocazione.
```
Con:
```
**Sempre, prima di `gh pr create`.** Il hook `pr-premortem-gate` blocca la creazione PR se non c'e' evidenza di invocazione, su qualsiasi repository git.
```

### Edit 3 — aggiungi sezione "Scope di attivazione" subito DOPO il blocco "Eccezioni" (dopo L54)

Inserisci verbatim:

```markdown

---

## Scope di attivazione

- **Default:** il gate scatta su qualsiasi repository git con remote `origin` configurato.
- **Opt-in legacy `itsiae/*`:** se vuoi limitare l'enforcement all'org `itsiae`, setta `DEVFORGE_GATE_SCOPE=itsiae` nel tuo shell init (`~/.zshrc` / `~/.bashrc`) oppure scrivi `itsiae` in `~/.claude/.devforge-gate-scope` (state file letto se la env var non propaga al subprocess hook).
- **Repo senza remote:** il gate fa no-op (early return). Lavora in locale come prima.

Vedi `hooks/ENV_VARS.md` § "Gate Scope" per i valori validi.
```

## Step 4 — Esegui e verifica che passa

```bash
bash tests/skill_premortem_generalized.test.sh
```

Atteso: `PASS: 6 / 6`, exit 0.

## Step 5 — Commit

```bash
git add skills/siae-premortem/SKILL.md tests/skill_premortem_generalized.test.sh
git commit -m "docs(skill): generalize siae-premortem (remove itsiae scope)

SKILL.md no longer hardcodes itsiae/* scope. New 'Scope di attivazione'
section documents DEVFORGE_GATE_SCOPE env + state file fallback.
6 verification tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `grep -c "on itsiae/\* repos" skills/siae-premortem/SKILL.md` = 0
- [ ] `grep -c "prima di .gh pr create. su .itsiae" skills/siae-premortem/SKILL.md` = 0
- [ ] `grep -c "^## Scope di attivazione$" skills/siae-premortem/SKILL.md` = 1
- [ ] `bash tests/skill_premortem_generalized.test.sh` exit 0 con `PASS: 6 / 6`
