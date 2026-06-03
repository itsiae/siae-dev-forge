# Few-Shot End-to-End — T1 Pure Logic Example

> Lazy-load: caricato in Phase 5 ALLA PRIMA invocazione del session.

## Source file (target)

`src/utils/format-currency.ts` (LOC: 28)

```typescript
export function formatCurrency(amount: number, currency: string = "EUR"): string {
  if (amount < 0) {
    throw new Error("Negative amount not allowed");
  }
  if (amount === 0) {
    return `0.00 ${currency}`;
  }
  const formatted = amount.toFixed(2);
  return `${formatted} ${currency}`;
}

export function parseCurrency(value: string): number {
  const match = value.match(/^([\d.]+)\s+([A-Z]{3})$/);
  if (!match) {
    throw new Error("Invalid currency format");
  }
  return parseFloat(match[1]);
}
```

## Pre-Generation grep

```bash
grep -nE "^export (default|const|function|class)" src/utils/format-currency.ts
# Output:
# 1:export function formatCurrency(amount: number, currency: string = "EUR"): string {
# 13:export function parseCurrency(value: string): number {
```

→ 2 named exports, 0 dependencies → tier T1, batch_ceiling=3.

## Generated test (output)

`src/utils/format-currency.test.ts` (LOC: 56)

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { formatCurrency, parseCurrency } from './format-currency'

beforeEach(() => { vi.clearAllMocks() })

describe('formatCurrency', () => {
  it('formats positive amount with default EUR', () => {
    // Arrange
    const amount = 100.5
    // Act
    const result = formatCurrency(amount)
    // Assert
    expect(result).toBe('100.50 EUR')
  })

  it('formats with custom currency code', () => {
    expect(formatCurrency(50, 'USD')).toBe('50.00 USD')
  })

  it('returns zero formatted when amount is 0', () => {
    expect(formatCurrency(0)).toBe('0.00 EUR')
    expect(formatCurrency(0, 'GBP')).toBe('0.00 GBP')
  })

  it('throws on negative amount', () => {
    expect(() => formatCurrency(-1)).toThrow('Negative amount not allowed')
    expect(() => formatCurrency(-0.01)).toThrow('Negative amount not allowed')
  })
})

describe('parseCurrency', () => {
  it('parses valid currency string', () => {
    expect(parseCurrency('100.50 EUR')).toBeCloseTo(100.5)
  })

  it('parses zero amount', () => {
    expect(parseCurrency('0 EUR')).toBe(0)
  })

  it('throws on malformed input', () => {
    expect(() => parseCurrency('invalid')).toThrow('Invalid currency format')
    expect(() => parseCurrency('100.50')).toThrow('Invalid currency format')
    expect(() => parseCurrency('100 USD EUR')).toThrow('Invalid currency format')
  })
})
```

## Coverage stimata

- Lines: 100% (tutte le righe coperte)
- Branches: 100% (3 branch: amount<0, amount==0, fallthrough; regex match/no-match)
- Functions: 2/2 = 100%

## Pattern applicati (AAA + edge cases)

| Pattern | Applicazione |
|---------|--------------|
| Happy path | `formatCurrency(100.5)` con default EUR |
| Edge case 1 | Custom currency `USD` |
| Edge case 2 | Boundary zero (input/output) |
| Negative path | Throw su negative amount + malformed regex |

## Tier classification

T1 — Pure Logic (0 imports esterni, 0 I/O, 0 framework). Batch_ceiling=3.

---

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
