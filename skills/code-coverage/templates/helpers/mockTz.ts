import { vi } from 'vitest'
/** Bypassa Intl/TZ: CI runner senza ICU full → RangeError: Invalid time zone. */
export function mockTz(utilsModulePath = '../libs/utils') {
  vi.mock(utilsModulePath, async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>()
    return { ...actual, getItalyOffset: vi.fn(() => 7200000), addItalyOffset: vi.fn((d: Date) => d) }
  })
}
