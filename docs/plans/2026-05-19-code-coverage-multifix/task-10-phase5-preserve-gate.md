# Task 10 — references/phase-5-generation.md: preserve-existing gate

**Fix-group:** G6
**ADR riferito:** ADR-6
**Stato:** [PENDING]
**Dipendenze:** —

## File modificati

- `skills/code-coverage/references/phase-5-generation.md`

## Implementazione

Aggiungi in cima a Phase-5 (Step 0 — Pre-write checklist):

```markdown
### Step 0 — Pre-write hard gate (PRESERVE_EXISTING)

Prima di QUALSIASI write in Phase 5, esegui:

\`\`\`bash
if [ -f "${TEST_PATH}" ]; then
  echo "[PRESERVE_EXISTING] test already exists at ${TEST_PATH}" \
    >> "${REPO}/.code-coverage/decisions.log"
  continue  # skip questo file, NON sovrascrivere
fi
\`\`\`

**Rationale (ADR-6):** brownfield repos hanno tipicamente test gia' scritti
dall'umano. Sovrascriverli e' violazione "never destroy user work". Block 9
elenchera' i file preservati con messaggio:
"M existing tests preserved (PRESERVE_EXISTING). Use /code-coverage --augment
per estendere coverage su moduli esistenti."

Convention naming `${TEST_PATH}`:
- JS/TS co-location: `${MODULE_DIR}/${MODULE_BASENAME}.test.${ext}`
- JS/TS __tests__: `${MODULE_DIR}/__tests__/${MODULE_BASENAME}.test.${ext}`
- Python pytest: `${TEST_ROOT}/test_${MODULE_BASENAME}.py`
- Java JUnit: `${TEST_ROOT}/${MODULE_BASENAME}Test.java`

Check entrambe le naming convention (co-located + __tests__) prima di concludere
che il test non esiste.
```

## Criterio di accettazione

- Phase-5 reference ha la sezione Step 0
- Riferimento a Block 9 PRESERVE_EXISTING decision log
- Convention naming per JS/TS/Python/Java tutte documentate
