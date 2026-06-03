import { vi } from 'vitest'
/**
 * Bypassa Intl/TZ: CI runner senza ICU full → RangeError: Invalid time zone.
 *
 * VINCOLO DI HOISTING VITEST: il path passato a vi.mock() DEVE essere un
 * string literal, NON una variabile o parametro. Vitest hoist-a vi.mock()
 * staticamente prima dell'esecuzione del modulo: un path dinamico non viene
 * risolto e il mock NON viene registrato (test verde falso).
 *
 * Il path literal sotto (`'../libs/utils'`) è il default SIAE. Adattalo al
 * path reale del tuo repo (es. `'../../shared/utils'`). Essendo un literal
 * non può essere parametrizzato: inlinea questa funzione nel tuo spec file
 * e sostituisci il literal direttamente.
 *
 * Offset hardcoded CEST (UTC+2, 7200000 ms): non asserire sull'offset esatto
 * per timestamp invernali (CET = UTC+1), poiché il mock non distingue stagioni.
 */
export function mockTz() {
  vi.mock('../libs/utils', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>()
    return { ...actual, getItalyOffset: vi.fn(() => 7200000), addItalyOffset: vi.fn((d: Date) => d) }
  })
}
