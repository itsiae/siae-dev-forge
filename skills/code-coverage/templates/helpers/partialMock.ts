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
