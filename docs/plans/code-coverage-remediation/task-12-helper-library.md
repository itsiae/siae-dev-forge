# Task 12 — Test-helper library + Phase 4 generation

**Goal:** Aggiungere i template degli helper di test riusabili (`mockTz`, `mockKnex`, `mockClass`, `partialMock`, `builderFactory`) e uno step Phase 4 che li materializza in `<repo>/src/__tests__/helpers/` se assenti (gate PRESERVE_EXISTING). Risolve gap 6.4/R4 (pattern mock scritti a mano in 4 commit). Gli helper alimentano le tecniche di WS-3/WS-4.

**WS:** WS-3 · **Dipendenze:** nessuna.

## File coinvolti
- Crea: `skills/code-coverage/templates/helpers/mockTz.ts`
- Crea: `skills/code-coverage/templates/helpers/mockKnex.ts`
- Crea: `skills/code-coverage/templates/helpers/mockClass.ts`
- Crea: `skills/code-coverage/templates/helpers/partialMock.ts`
- Crea: `skills/code-coverage/templates/helpers/builderFactory.ts`
- Modifica: `skills/code-coverage/references/phase-5-generation.md` (sezione "Test Helper Auto-Import")
- Modifica: `skills/code-coverage/SKILL.md` (Phase 4: step helper-generation)

## Step 1 — Crea gli helper

`templates/helpers/mockTz.ts`:
```typescript
import { vi } from 'vitest'
/** Bypassa Intl/TZ: CI runner senza ICU full → RangeError: Invalid time zone. */
export function mockTz(utilsModulePath = '../libs/utils') {
  vi.mock(utilsModulePath, async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>()
    return { ...actual, getItalyOffset: vi.fn(() => 7200000), addItalyOffset: vi.fn((d: Date) => d) }
  })
}
```

`templates/helpers/mockKnex.ts`:
```typescript
import { vi } from 'vitest'
/** Factory per un Knex query builder chainable mockato. */
export function mockKnex(result: unknown[] = []) {
  const qb: Record<string, unknown> = {}
  for (const m of ['select', 'from', 'where', 'whereIn', 'join', 'leftJoin',
                    'orderBy', 'groupBy', 'limit', 'offset', 'returning', 'insert',
                    'update', 'del', 'first']) {
    qb[m] = vi.fn(() => qb)
  }
  qb.then = (resolve: (v: unknown) => void) => resolve(result)
  return qb
}
```

`templates/helpers/mockClass.ts`:
```typescript
import { vi } from 'vitest'
/** Crea un mock di classe: vi.fn().mockImplementation con i metodi richiesti. */
export function mockClass(methods: string[], impl: Record<string, unknown> = {}) {
  return vi.fn().mockImplementation(() => {
    const inst: Record<string, unknown> = {}
    for (const m of methods) inst[m] = impl[m] ?? vi.fn()
    return inst
  })
}
```

`templates/helpers/partialMock.ts`:
```typescript
import { vi } from 'vitest'
/** Partial module mock: mantiene l'originale e sovrascrive solo le chiavi indicate. */
export function partialMock<T extends Record<string, unknown>>(
  modulePath: string, overrides: Partial<T>,
) {
  vi.mock(modulePath, async (importOriginal) => {
    const actual = await importOriginal<T>()
    return { ...actual, ...overrides }
  })
}
```

`templates/helpers/builderFactory.ts`:
```typescript
/** Genera due fixture per file ??-heavy: minimal (rami fallback) + full (rami value). */
export function buildFixtures<T extends Record<string, unknown>>(
  fullShape: T,
): { minimal: Partial<T>; full: T } {
  return { minimal: {}, full: fullShape }
}
```

## Step 2 — Documenta auto-import in `phase-5-generation.md`
Aggiungi:
```markdown
## Test Helper Auto-Import

In Phase 4, se assenti, vengono materializzati in `<repo>/<src>/__tests__/helpers/`
i template da `templates/helpers/` (gate PRESERVE_EXISTING: non sovrascrivere helper esistenti).
Ogni spec generato importa l'helper rilevante:
- `scan_tz_usage.py.uses_tz` → `import { mockTz } from '...helpers/mockTz'`
- `scan_class_instantiations.py` non vuoto → `import { mockClass } from '...helpers/mockClass'`
- DAO/Knex → `import { mockKnex } from '...helpers/mockKnex'`
- file con `branch_operator_count > 40` → `import { buildFixtures } from '...helpers/builderFactory'`
```

## Step 3 — Documenta lo step in `SKILL.md` Phase 4
Nella Phase 4 (env prep), aggiungi una riga:
```markdown
**Phase 4 — Test helpers:** se `<repo>/<src>/__tests__/helpers/` non contiene gli helper,
copia da `templates/helpers/*.ts` (PRESERVE_EXISTING: skip se già presenti). Log in decisions.log.
```

## Step 3-bis — ICU probe in Phase 4 (chiude WS-3.2 del design)
Aggiungi in `SKILL.md` Phase 4, subito dopo lo step helpers, la nota ICU probe:
```markdown
**Phase 4 — ICU probe:** se un file under test ha `scan_tz_usage.py.uses_tz==true`, verifica
che il runtime Node abbia ICU full: `node -e "new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome'}).format(new Date())"`.
Se fallisce con RangeError → forza l'import di `mockTz` negli spec TZ-dipendenti (il mock
bypassa Intl) e logga `[phase4] ICU probe failed → mockTz forced` in decisions.log.
```

## Step 4 — Verifica
Run: `for f in mockTz mockKnex mockClass partialMock builderFactory; do test -f skills/code-coverage/templates/helpers/$f.ts && echo "$f OK"; done`
Output atteso: 5 righe `... OK`.
Run: `grep -q "Test Helper Auto-Import" skills/code-coverage/references/phase-5-generation.md && echo OK` → `OK`.
Run (sintassi TS, se `npx` disponibile): `npx --yes tsc --noEmit --strict skills/code-coverage/templates/helpers/*.ts 2>&1 | head` → nessun errore di parsing bloccante (gli import di vitest sono risolti a runtime nel repo target; in caso di errore "Cannot find module 'vitest'" è atteso e non blocca, perché il check è solo sintattico).

## Step 5 — Commit
```
git add skills/code-coverage/templates/helpers skills/code-coverage/references/phase-5-generation.md skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): reusable test-helper library (mockTz/mockKnex/mockClass/partialMock/builderFactory)"
```

## Criteri di accettazione
- [ ] 5 file helper esistono in `templates/helpers/`.
- [ ] `phase-5-generation.md` documenta l'auto-import e le condizioni.
- [ ] `SKILL.md` Phase 4 menziona la generazione helper con gate PRESERVE_EXISTING.
