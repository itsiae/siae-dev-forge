# Task 13 — Anti-pattern + few-shot branch-matrix

**Goal:** Documentare l'anti-pattern "vi.fn() piatto per classi istanziate con `new`" in `assets/anti-patterns.md` (BAD/GOOD) e aggiungere un esempio few-shot branch-matrix in `assets/few-shot-e2e.md`. Consolida le tecniche di WS-2/WS-3 in materiale di riferimento che la skill carica in Phase 5.

**WS:** WS-3 · **Dipendenze:** Task 07 (template branch-matrix), Task 10 (class-mock).

## File coinvolti
- Modifica: `skills/code-coverage/assets/anti-patterns.md`
- Modifica: `skills/code-coverage/assets/few-shot-e2e.md`

## Step 1 — Aggiungi anti-pattern
In `skills/code-coverage/assets/anti-patterns.md`, aggiungi in coda:

````markdown
## Anti-pattern: vi.fn() piatto per classi istanziate con `new`

Quando il source-under-test fa `new SpazioDao()` inline, mockare solo le funzioni
non basta: la classe va mockata come costruttore.

### BAD
```typescript
vi.mock('../dao/SpazioDao', () => ({ retrieveAccertamentiApp: vi.fn() }))
// ❌ SpazioDao resta la classe reale → new SpazioDao() istanzia il codice vero,
//    i branch interni non sono isolati, il test può rompersi su dipendenze DB.
```

### GOOD
```typescript
vi.mock('../dao/SpazioDao', () => ({
  SpazioDao: vi.fn().mockImplementation(() => ({
    retrieveAccertamentiApp: vi.fn().mockResolvedValue([]),
    findById: vi.fn().mockResolvedValue(null),
  })),
}))
// ✅ Il costruttore è mockato; ogni new SpazioDao() ritorna l'istanza fake.
```
Vedi `scan_class_instantiations.py` per estrarre i metodi da mockare.
````

## Step 2 — Aggiungi few-shot branch-matrix
In `skills/code-coverage/assets/few-shot-e2e.md`, aggiungi una sezione:

````markdown
## Few-shot: branch-matrix per file ??-heavy

Source (`LocaleDao.ts`, estratto):
```typescript
export function assemblaLocale(row: LocaleRow) {
  return { denominazione: row.denom ?? '', citta: row.citta ?? 'N/D' }
}
```

Test branch-matrix generato (un blocco per ogni `??`):
```typescript
import { describe, it, expect } from 'vitest'
import { assemblaLocale } from './LocaleDao'

describe('assemblaLocale — branch matrix', () => {
  describe('denom fallback', () => {
    it('returns "" when denom is null', () =>
      expect(assemblaLocale({ denom: null, citta: 'Roma' }).denominazione).toBe(''))
    it('returns "" when denom is undefined', () =>
      expect(assemblaLocale({ citta: 'Roma' } as any).denominazione).toBe(''))
    it('returns value when denom is present', () =>
      expect(assemblaLocale({ denom: 'Teatro', citta: 'Roma' }).denominazione).toBe('Teatro'))
  })
  describe('citta fallback', () => {
    it('returns "N/D" when citta is null', () =>
      expect(assemblaLocale({ denom: 'X', citta: null }).citta).toBe('N/D'))
    it('returns value when citta is present', () =>
      expect(assemblaLocale({ denom: 'X', citta: 'Milano' }).citta).toBe('Milano'))
  })
})
```
````

## Step 3 — Verifica
Run: `grep -q "vi.fn() piatto per classi" skills/code-coverage/assets/anti-patterns.md && echo OK` → `OK`.
Run: `grep -q "branch-matrix per file" skills/code-coverage/assets/few-shot-e2e.md && echo OK` → `OK`.

## Step 4 — Commit
```
git add skills/code-coverage/assets/anti-patterns.md skills/code-coverage/assets/few-shot-e2e.md
git commit -m "docs(code-coverage): add class-mock anti-pattern + branch-matrix few-shot example"
```

## Criteri di accettazione
- [ ] `anti-patterns.md` contiene il blocco BAD/GOOD class-mock.
- [ ] `few-shot-e2e.md` contiene l'esempio branch-matrix con i 3 rami.
