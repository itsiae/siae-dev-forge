---
task: 06
title: brainstorming-gate — dual-write + rimozione W2_DEFAULT=0 escape (ADR-006)
size: M
blocks: [13]
depends: [02, 03]
---

# Task 6 — brainstorming-gate task-scoped + W2 cleanup

Rimuove escape hatch `W2_DEFAULT=0` (gate sempre attivo). Migra a task-scoped.
Estende scope a `.tf/.hcl` via file-taxonomy.

## Change summary

### Rimozioni

1. Rimuovere linee 88-93 del `hooks/brainstorming-gate`:

   ```bash
   W2_DEFAULT="${DEVFORGE_W2_DEFAULT:-0}"
   if [ "$W2_DEFAULT" != "1" ] && [ "${DEVFORGE_ENFORCEMENT_STRICT:-0}" != "1" ]; then
       echo '{}'
       exit 0
   fi
   ```

   Il gate diventa sempre attivo (coerente con `hooks.json` + `DEVFORGE_ENFORCEMENT_OFF=1` come escape globale preservato).

2. Rimuovere regex `PROD_EXTENSIONS` hardcoded → sostituire con
   `devforge_file_requires_brainstorming "$FILE_PATH"` (include .tf/.hcl ora).

### Additions

1. Load `lib/task-id.sh` + `lib/file-taxonomy.sh` + `lib/evidence-check.sh`
2. Check path:
   - Task-scope: `devforge_task_skill_validated "$TASK_ID" siae-brainstorming`
   - Evidence: `_devforge_check_design_doc_produced`
   - Dual-write divergence log
3. Counter `brainstorm-counter` → task-scoped (per task_id invece di per SID)

### Progressive friction preservata

Il comportamento progressive (warn nudge 1° edit, warn block 2-3°, hard block 4°)
rimane. Solo il counter passa da SID-anchored a task-anchored.

```bash
COUNTER_FILE="${HOME}/.claude/.devforge-task-skills/${TASK_ID}/brainstorm-counter"
```

### Bypass preservato

`DEVFORGE_SKIP_BRAINSTORMING=1` + abuse tracking intatto. Aggiunta:
contatore per-task (oltre che daily) — se stesso task viene bypassato >2
volte, log `bypass_repeated_same_task`.

## Edge cases

- **.tf file**: ora triggera gate (prima no) → prima volta che user tocca
  Terraform senza brainstorm, vedrà nudge
- **Task_id vuoto** (non-itsiae): skip (come oggi)
- **Task_id change mid-session con design revised**: evidence carry-forward
  → counter reset (sono task nuovi ma con validated skill carry)

## Acceptance

- [ ] Rimosso early-exit `W2_DEFAULT!=1`
- [ ] Integrato `lib/file-taxonomy.sh` (include .tf/.hcl)
- [ ] Integrato `lib/task-id.sh` (counter task-scoped)
- [ ] `DEVFORGE_USE_SESSION_SCOPE=1` ripristina SID-anchored counter
- [ ] `DEVFORGE_SKIP_BRAINSTORMING=1` + abuse tracking preservato
- [ ] Shadow-check divergence log
- [ ] Test `tests/hooks/test_brainstorming_gate_task_scope.sh`:
  - [ ] .tf edit senza brainstorm → warn/block
  - [ ] progressive counter task-scoped
  - [ ] bypass daily counter
  - [ ] rollback env var
  - [ ] gate sempre attivo (nessun W2 skip)

## Out of scope

- Modifica `hooks.json` (default sempre attivo) → task 12
- Documentazione env var → task 14 README
