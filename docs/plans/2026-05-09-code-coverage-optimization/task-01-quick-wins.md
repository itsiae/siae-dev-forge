# Task 01 — Quick Wins (P1, P2, P6, P12 + QW1-QW10)

**Goal:** Eliminare ~13 approval gates runtime, rimuovere coverage gate intermedi, attivare hard gate placeholder pre-write, rendere conditional gli OUTPUT blocks 4/6/9, fix template `restoreAllMocks` redundante. Tutto via modifiche markdown/JSON senza nuovi script.

**SP:** 1 (Augmented)
**Fix IDs covered:** P1 + P2 + P6 + P12 + QW1-QW10
**Branch:** `feat/code-coverage-opt-quick-wins`
**Dipendenze:** task-00 (baseline raccolta)

---

## File coinvolti

**Modifica**:
- `skills/code-coverage/SKILL.md` (≈30 LOC modificate)
- `skills/code-coverage/references/phase-1-discovery.md` (rimuovi righe 168-185 Quick Sizing + righe 230-233 remote handling approval)
- `skills/code-coverage/references/phase-3-sizing.md` (rimuovi righe 89-92 batch plan approval)
- `skills/code-coverage/references/phase-4-environment.md` (rimuovi riga 72 wait-for-approval + righe 50-66 Pre-Existing Coverage Pass + riga 221 vitest config approval)
- `skills/code-coverage/references/phase-5-generation.md` (rimuovi righe 71-72 file list approval + righe 42-50 P2 Early-Exit Checkpoint)
- `skills/code-coverage/references/phase-6-coverage.md` (rimuovi riga 172 CI integration approval)
- `skills/code-coverage/references/phase-7-repair.md` (rimuovi riga 93 snapshot approval + righe 130-140 ASK USER early-abort)
- `skills/code-coverage/templates/vitest.template.ts` (riga 25: rimuovi `afterEach(restoreAllMocks)`)
- `skills/code-coverage/commands/code-coverage.md` (verifica: già conditional su args)

**Creazione**:
- `skills/code-coverage/lib/placeholder-check.sh` (nuovo helper bash, ~15 LOC) per P6 hard gate

---

## Step bite-sized

### Step 1 — Backup + branch

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-quick-wins
```

### Step 2 — SKILL.md: riscrivi Principle 1 (P1)

In `skills/code-coverage/SKILL.md` riga 37 sostituisci il testo da:
```
1. **Never mutate the target repository without explicit user approval.** Every `npm install`, file write, config change, or directory creation in the target repo requires a user confirmation step before execution.
```
A:
```
1. **Autonomous Execution Policy.** Invocazione di `/code-coverage` costituisce blanket approval per tutte le operazioni di lettura/scrittura/install nel target repo per la durata della sessione. Mutazioni ammesse: (a) directory `.code-coverage/` come workdir, (b) file di test in directory test convenzionali (`__tests__`, `tests/`, `*.test.*`, `*.spec.*`), (c) `vitest.config.ts` o `jest.config.ts` SOLO se assenti, (d) install di `devDependencies` esclusivamente. Mai modificare codice di produzione. Tutte le decisioni sono loggate in `.code-coverage/decisions.log`. ZERO prompt utente runtime.
```

### Step 3 — SKILL.md: rimuovi APPROVAL REQUEST TEMPLATES (P1)

Cancella interamente la sezione `## APPROVAL REQUEST TEMPLATES` (righe 220-239).

### Step 4 — SKILL.md: aggiorna INPUT MODE (P1, QW1)

Sostituisci il blocco `## INPUT MODE — Identify Target Repository` (righe 16-29) con:
```
## INPUT MODE — Identify Target Repository

Politica deterministica autonoma:
- Se invocata con argomento valido (path locale assoluto OR URL GitHub): usa quello.
- Se invocata senza argomenti: usa `$(pwd)` come local path target.
- Se URL GitHub senza branch/subdirectory: branch=`main`, subdirectory=root.
- Se URL malformato o path inesistente: emit single error message and STOP.

Mai chiedere conferma o input. La skill è progettata per esecuzione completamente autonoma.
```

### Step 5 — SKILL.md: rimuovi Phase 5 Coverage Gate + P2 Checkpoint (P2)

Cancella interamente le righe 114-126 (la sezione `**Coverage Gate (MEDIUM/LARGE/VERY_LARGE repos only):**` fino alla fine del blocco con i tre bullet di Early Stop / 55-70% / <55%).

### Step 6 — SKILL.md: rimuovi Phase 4 Pre-Existing Coverage Pass (P2)

In Phase 4 (riga 99) aggiungi nota:
```
**Pre-existing coverage skip**: Phase 1 ha già letto eventuali `coverage/lcov.info`, `target/site/jacoco/index.html`, `coverage.json` (mtime < 7 giorni). Se `pre_existing_coverage_pct ≥ 70%`, emit Block 8 con valore corrente e END. Altrimenti procedi.
```

(La rimozione del Pre-Existing Coverage Pass standalone in Phase 4 viene completata in `phase-4-environment.md` step 8.)

### Step 7 — SKILL.md: OUTPUT blocks conditional (P12)

Sostituisci riga 161 `At skill completion, emit all 9 blocks in order. Do not skip any block.` con:
```
At skill completion, emit blocks in order. Block 1, 5, 8 sono SEMPRE presenti. Block 4, 6, 9 sono CONDIZIONALI:
- Block 4 (`unsupported_groups`): emit ONLY se array non vuoto.
- Block 6 (`Dependency Install Commands`): emit ONLY se `validate_env.py install_commands` non vuoto.
- Block 9 (`Next Actions`): emit ONLY se ci sono moduli sotto threshold OPPURE follow-up batch attivo OPPURE manual tests suggested.

Condizionalità valutata da check programmatico (file presence, JSON field empty), MAI prompt utente.
```

### Step 8 — `phase-1-discovery.md`: rimuovi Quick Sizing Pass (QW2)

Cancella le righe 168-185 (sezione "Quick Sizing Pass").

### Step 9 — `phase-1-discovery.md`: rimuovi remote clone approval (P1)

Riga 230-233, sostituisci `Present the clone command to the user and request approval` con:
```
Auto-clone in `mktemp -d` senza prompt. Cleanup automatico al termine della sessione. Path temp loggato in `.code-coverage/decisions.log`.
```

### Step 10 — `phase-3-sizing.md`: rimuovi batch plan approval (P1)

Cancella righe 89-92 (la sezione che inizia con `Do you approve saving the batch plan?`). Sostituisci con:
```
Persisti `batch-plan.json` autonomamente in `.code-coverage/`. Emetti messaggio informativo: `Switching to phased enterprise mode. Batch plan saved to .code-coverage/batch-plan.json`.
```

### Step 11 — `phase-4-environment.md`: rimuovi install wait-for-approval (P1)

Riga 72, sostituisci `Present these to the user and **wait for approval** before executing.` con:
```
Esegui install autonomamente nel target repo. Snapshot lockfile pre-install: `cp package-lock.json .code-coverage/lockfile.bak` (o equivalente per altro PM). Se exit-code ≠ 0, ripristina lockfile e log error in `.code-coverage/decisions.log`. Tutte le install loggate in `.code-coverage/install-log.txt`.
```

### Step 12 — `phase-4-environment.md`: rimuovi Pre-Existing Coverage Pass (P2)

Cancella interamente le righe 48-66 (sezione "Pre-Existing Coverage Pass"). La logica viene assorbita da Phase 1 lcov.info parse + skip gate (vedi step 6).

### Step 13 — `phase-4-environment.md`: rimuovi vitest config approval (P1)

Riga 221, sostituisci `do not write without approval` con:
```
Genera e scrivi `vitest.config.ts` o `jest.config.ts` autonomamente SOLO se assente. Mai sovrascrivere config esistenti. Decisione loggata in `.code-coverage/decisions.log`.
```

### Step 14 — `phase-5-generation.md`: rimuovi file list approval (P1)

Cancella righe 71-72 della Pre-Generation Checklist (lo step "Request approval before writing any file to disk."). Sostituisci con:
```
5. **Hard gate placeholder check** (P6): per ogni file da scrivere, esegui `bash skills/code-coverage/lib/placeholder-check.sh <file>`. Se exit-code ≠ 0 → fail loudly, NON scrivere il file, log in `.code-coverage/decisions.log`.
6. Persisti la lista files in `.code-coverage/generation-plan.txt` per traceability, poi procedi con write autonomamente.
```

### Step 15 — `phase-5-generation.md`: rimuovi P2 Early-Exit Checkpoint (P2)

Cancella le righe 42-50 (sezione "P2 Early-Exit Checkpoint").

### Step 16 — `phase-6-coverage.md`: rimuovi CI integration approval (P1)

Riga 172, sostituisci `with user approval` con:
```
emit suggested CI snippet in OUTPUT Block 9 come "Recommended CI integration step". Mai modificare file CI esistenti.
```

### Step 17 — `phase-7-repair.md`: rimuovi snapshot approval (P1)

Riga 93, sostituisci `with user approval` con:
```
applica `vitest --update-snapshots` autonomamente SOLO se: (a) iter > 1, AND (b) failure category == "snapshot mismatch", AND (c) intentional change documentato in `.code-coverage/decisions.log`.
```

### Step 18 — `phase-7-repair.md`: rimuovi ASK USER early-abort (P1)

Cancella le righe 130-140 (early abort check con `ASK user`). Sostituisci con:
```
**Autonomous early-abort policy**: dopo iter==1, se `global_coverage < 30% AND any P1 < 40%`:
1. Imposta `loop_max_remaining = 1` (1 sola iter aggiuntiva)
2. Log: `WARN: critical low coverage, single retry attempted` in `.code-coverage/decisions.log`
3. Dopo iter==2, se `global_coverage < 50%`: emit best-effort report e STOP.

Nessun prompt utente. Decisione totalmente deterministica.
```

### Step 19 — `vitest.template.ts`: fix `restoreAllMocks` redundante (QW6)

In `skills/code-coverage/templates/vitest.template.ts` riga 25, cancella la linea:
```typescript
afterEach(() => { vi.restoreAllMocks() })
```

Aggiungi commento alla riga 23 (sopra `beforeEach`):
```typescript
// Mock cleanup strategy:
// - DEFAULT: vi.clearAllMocks() in beforeEach (resetta calls/instances)
// - Aggiungi afterEach(vi.restoreAllMocks()) SOLO se il file usa vi.spyOn()
//   (non necessario se usi solo vi.mock()/vi.fn())
```

### Step 20 — Crea `placeholder-check.sh` (P6)

Crea `skills/code-coverage/lib/placeholder-check.sh` con questo contenuto:

```bash
#!/usr/bin/env bash
# placeholder-check.sh — hard gate per file di test generati
# Usage: bash placeholder-check.sh <file-path>
# Exit 0 se nessun placeholder trovato, exit 1 altrimenti

set -euo pipefail

FILE="${1:?file path required}"

if [ ! -f "$FILE" ]; then
  echo "ERROR: $FILE does not exist" >&2
  exit 1
fi

MATCHES=$(grep -nE '\{\{[A-Z_]+\}\}' "$FILE" || true)

if [ -n "$MATCHES" ]; then
  echo "PLACEHOLDER LEAK in $FILE:" >&2
  echo "$MATCHES" >&2
  echo "Refusing to write file with unresolved placeholders." >&2
  exit 1
fi

echo "OK: no placeholder in $FILE"
exit 0
```

Make executable:
```bash
chmod +x skills/code-coverage/lib/placeholder-check.sh
```

### Step 21 — Test smoke `placeholder-check.sh`

Test caso PASS:
```bash
echo "const x = 1; // valid" > /tmp/test-pass.ts
bash skills/code-coverage/lib/placeholder-check.sh /tmp/test-pass.ts
echo "Exit: $?"
```
Output atteso:
```
OK: no placeholder in /tmp/test-pass.ts
Exit: 0
```

Test caso FAIL:
```bash
echo "import { {{DepMethod}} } from '{{DEP_PATH}}';" > /tmp/test-fail.ts
bash skills/code-coverage/lib/placeholder-check.sh /tmp/test-fail.ts
echo "Exit: $?"
```
Output atteso:
```
PLACEHOLDER LEAK in /tmp/test-fail.ts:
1:import { {{DepMethod}} } from '{{DEP_PATH}}';
Refusing to write file with unresolved placeholders.
Exit: 1
```

### Step 22 — Spec-reviewer

Lancia spec-reviewer con design doc `2026-05-09-code-coverage-optimization-design.md` e PR diff. Risolvi BLOCK/WARN fino a PASS.

### Step 23 — Commit + PR

```bash
git add skills/code-coverage/SKILL.md \
        skills/code-coverage/references/phase-{1,3,4,5,6,7}-*.md \
        skills/code-coverage/templates/vitest.template.ts \
        skills/code-coverage/lib/placeholder-check.sh
git commit -m "feat(code-coverage): quick wins — remove approval gates, add placeholder check

P1: rimossi ~13 approval gates runtime; auto-execution policy
P2: rimossi Phase 5 P1 Gate + P2 Checkpoint + Pre-Existing Coverage Pass
P6: hard gate placeholder pre-write via lib/placeholder-check.sh
P12: OUTPUT blocks 4/6/9 conditional via check programmatico
QW6: fix vitest.template.ts (rimosso restoreAllMocks redundante)

Refs design doc 2026-05-09-code-coverage-optimization-design.md §3.1, §4.2 PR1.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-quick-wins
gh pr create --title "feat(code-coverage): quick wins (P1, P2, P6, P12)" --body "$(cat <<'EOF'
## Summary
- Rimossi ~13 approval gates runtime (P1)
- Eliminati coverage gate intermedi: solo Phase 6 + max 1 Phase 7/iter (P2)
- Aggiunto hard gate placeholder check pre-write (P6)
- OUTPUT blocks 4/6/9 conditional (P12)
- Fix template restoreAllMocks redundante (QW6)

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR1

## Test plan
- [x] placeholder-check.sh smoke test pass/fail
- [ ] Run /code-coverage su benchmark MEDIUM, verifica zero round-trip
- [ ] Conferma riduzione >=2 coverage runs vs baseline
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] SKILL.md contiene Principle 1 riscritto (Autonomous Execution Policy)
- [ ] APPROVAL REQUEST TEMPLATES section cancellata
- [ ] INPUT MODE deterministico (cwd default + auto-clone)
- [ ] Tutte le 13 occorrenze di `[Y/n]` / `wait for approval` / `request approval` rimosse: verificabile con `grep -rE '\[Y/n\]|wait for approval|request approval' skills/code-coverage/` → output vuoto
- [ ] `placeholder-check.sh` esiste, eseguibile, smoke test pass/fail OK
- [ ] `vitest.template.ts` non contiene più `afterEach(.*restoreAllMocks)`
- [ ] Phase 5 Coverage Gate + P2 Early-Exit Checkpoint cancellati
- [ ] Pre-Existing Coverage Pass standalone cancellato da Phase 4
- [ ] Spec-reviewer PASS
- [ ] PR aperta con descrizione completa

## Note operative

- Questo task non introduce script Python nuovi: solo bash + markdown edit
- Nessun test unitario aggiunto (è tutto config/markdown). Smoke test su placeholder-check.sh sufficiente
- Post-merge: ri-eseguire `tools/benchmark-skill.sh /tmp/bench-medium post-pr1` per validare che round-trip = 0
