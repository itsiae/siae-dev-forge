# Task 07 — Template `vitest-branch-matrix` + dual-fixture

**Goal:** Nuovo template `templates/vitest-branch-matrix.template.ts` che, in modalità `branch-priority`, genera 3 `it()` per ogni operatore di fallback (null / undefined / present) + regola dual-fixture (minimal + full-populated) per file con `branch_operator_count > 40`. Aggiorna `phase-5-generation.md` e `SKILL.md` Principio 5. Risolve gap 6.6/6.7.

**WS:** WS-2 · **Dipendenze:** Task 05 (branch count).

## File coinvolti
- Crea: `skills/code-coverage/templates/vitest-branch-matrix.template.ts`
- Modifica: `skills/code-coverage/references/phase-5-generation.md` (sezione "Coverage Requirements Per Module" + Dual-Fixture Rule)
- Modifica: `skills/code-coverage/SKILL.md` (Principio 5)

## Step 1 — Crea il template
Crea `skills/code-coverage/templates/vitest-branch-matrix.template.ts`:

```typescript
/**
 * VITEST BRANCH-MATRIX TEMPLATE
 * ====================================================================
 * Usato quando coverage_mode == "branch-priority" (vedi classify_coverage_mode.py).
 * Per OGNI operatore di fallback (?? / || / && / ?:) trovato nel source-under-test
 * genera 3 test: ramo null, ramo undefined, ramo present.
 * Placeholder {{CLASS_MOCK_BLOCK}} e {{TZ_MOCK_BLOCK}} sostituiti dai task WS-3.
 * ====================================================================
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_EXPORTS}} } from '{{SUT_PATH}}'
// {{CLASS_MOCK_BLOCK}}
// {{TZ_MOCK_BLOCK}}

describe('{{SUT_NAME}} — branch matrix', () => {
  beforeEach(() => { vi.clearAllMocks() })

  // ── Ripeti questo describe() per OGNI operatore trovato da count_branch_operators.py
  describe('{{FIELD_NAME}} fallback branch', () => {
    it('returns fallback when {{FIELD_NAME}} is null', () => {
      const fixture = { ...{{BASE_FIXTURE}}, {{FIELD_NAME}}: null }
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{FALLBACK_VALUE}})
    })

    it('returns fallback when {{FIELD_NAME}} is undefined', () => {
      const fixture = { ...{{BASE_FIXTURE}} }
      delete (fixture as Record<string, unknown>).{{FIELD_NAME}}
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{FALLBACK_VALUE}})
    })

    it('returns value when {{FIELD_NAME}} is present', () => {
      const fixture = { ...{{BASE_FIXTURE}}, {{FIELD_NAME}}: {{SAMPLE_VALUE}} }
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{SAMPLE_VALUE}})
    })
  })

  // ── Dual-fixture (solo se branch_operator_count > 40)
  // {{DUAL_FIXTURE_BLOCK}} es:
  //   const minimalFixture = {}
  //   const fullFixture = { /* TUTTI i campi opzionali valorizzati */ }
  //   it('with all optional fields populated', () => {
  //     expect({{SUT_FUNCTION}}(fullFixture)).toMatchObject({ /* valori attesi */ })
  //   })
})
```

## Step 2 — Aggiorna `references/phase-5-generation.md`
Nella sezione "Coverage Requirements Per Module" (intorno alla tabella `Happy path | Edge case 1 | ...`), aggiungi una sotto-sezione:

```markdown
### Branch-matrix mode (coverage_mode == "branch-priority")

Quando `batch-plan.json.files[].coverage_mode == "branch-priority"`, usa il template
`templates/vitest-branch-matrix.template.ts` invece del template standard. Per OGNI
operatore `??` / `||` / `&&` / `?:` riportato in `.code-coverage/branch-count/<file>.json`
genera 3 test: ramo null, ramo undefined, ramo present. La line coverage è gratis;
l'obiettivo è la branch matrix.

### Dual-Fixture Rule (branch_operator_count > 40)

Se il file ha `branch_operator_count > 40` (tipico dei mapper con molti `?? ""`),
genera DUE fixture:
- `minimalFixture = {}` → esercita tutti i rami fallback;
- `fullFixture` con TUTTI i campi opzionali valorizzati → esercita tutti i rami value-present.
Aggiungi un test `it('with all optional fields populated', ...)` che usa `fullFixture`.
```

## Step 3 — Aggiorna `SKILL.md` Principio 5
Trova il Principio 5 (riga ~38, "Coverage targets per-priority; global floor 70%") e sostituiscilo con:

```markdown
5. **Coverage targets line E branch separati.** Global floor 70% line. Branch target
   = `user-choice.json.target_branch` (può essere alzato da soglia CI, vedi Phase 2.5).
   Per file con `coverage_mode == branch-priority` (branch-heavy o branch lontana dal
   target) usa il template branch-matrix: la line non basta, conta la branch matrix.
```

## Step 4 — Verifica
Run: `bash skills/code-coverage/lib/placeholder-check.sh skills/code-coverage/templates/vitest-branch-matrix.template.ts`
Output atteso: il file è un template con placeholder `{{...}}` validi (placeholder-check NON deve fallire sui placeholder di template — verifica che lo script tratti i template come tali; in caso contrario, registra il template nell'allowlist usata da placeholder-check).
Run: `grep -c "{{" skills/code-coverage/templates/vitest-branch-matrix.template.ts` → atteso ≥ 10.
Run: `grep -q "branch-matrix mode" skills/code-coverage/references/phase-5-generation.md && echo OK` → `OK`.
Run: `grep -q "line E branch separati" skills/code-coverage/SKILL.md && echo OK` → `OK`.

## Step 5 — Commit
```
git add skills/code-coverage/templates/vitest-branch-matrix.template.ts skills/code-coverage/references/phase-5-generation.md skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): add branch-matrix template + dual-fixture rule + branch-aware principle"
```

## Criteri di accettazione
- [ ] Template esiste con i 3 blocchi `it()` (null/undefined/present) e placeholder dual-fixture.
- [ ] `phase-5-generation.md` contiene "Branch-matrix mode" e "Dual-Fixture Rule".
- [ ] `SKILL.md` Principio 5 menziona line E branch separati + branch-priority.
