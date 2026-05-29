import { vi } from 'vitest'
/**
 * PATTERN REFERENCE — Non usare questa funzione così com'è.
 *
 * VINCOLO DI HOISTING VITEST: vi.mock() richiede un path LITERAL hoistabile.
 * Vitest hoist-a vi.mock() staticamente prima dell'esecuzione del modulo:
 * passare `modulePath` come parametro di runtime significa che il path NON
 * può essere risolto → il mock NON viene registrato (test verde falso).
 *
 * Un wrapper runtime generico con path dinamico è strutturalmente impossibile.
 *
 * INVECE, inlinea il pattern seguente nel tuo spec file, sostituendo
 * '<modulePath>' con il literal reale del modulo da mockare:
 *
 * @example
 * // Nel tuo spec file (es. myService.spec.ts):
 * import { vi } from 'vitest'
 *
 * vi.mock('<modulePath>', async (importOriginal) => {
 *   const actual = await importOriginal<Record<string, unknown>>()
 *   return {
 *     ...actual,
 *     myMethod: vi.fn().mockResolvedValue({ id: 1 }),
 *     anotherMethod: vi.fn().mockReturnValue(42),
 *   }
 * })
 *
 * Esempio concreto con path reale:
 * vi.mock('../services/userService', async (importOriginal) => {
 *   const actual = await importOriginal<Record<string, unknown>>()
 *   return { ...actual, findUser: vi.fn().mockResolvedValue({ id: 1, name: 'Test' }) }
 * })
 */
export function partialMock<T extends Record<string, unknown>>(
  _modulePath: string,
  _overrides: Partial<T>,
): void {
  // Questo export è intenzionalmente non-op: il mock con path dinamico non
  // funziona per il vincolo di hoisting Vitest. Vedi JSDoc sopra per il
  // pattern corretto da inlinare nel proprio spec file.
  throw new Error(
    'partialMock() non può essere usata a runtime: vi.mock() richiede un path '
    + 'literal hoistabile. Inlinea il pattern mostrato nel JSDoc di questo file.',
  )
}
