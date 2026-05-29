import { vi } from 'vitest'
/**
 * Factory per un Knex query builder chainable mockato.
 *
 * @param result  - Array di risultati restituiti dalla query (default: []).
 * @param error   - Se fornito, la promise viene rifiutata con questo errore
 *                  invece di essere risolta con `result`.
 *
 * Il metodo `then` è conforme al contratto Thenable (PromiseLike):
 * accetta sia `onFulfilled` che `onRejected` come fa una Promise nativa.
 */
export function mockKnex(result: unknown[] = [], error?: Error) {
  const qb: Record<string, unknown> = {}
  for (const m of ['select', 'from', 'where', 'whereIn', 'join', 'leftJoin',
                    'orderBy', 'groupBy', 'limit', 'offset', 'returning', 'insert',
                    'update', 'del', 'first']) {
    qb[m] = vi.fn(() => qb)
  }
  qb.then = (
    resolve: (v: unknown) => void,
    reject?: (e: unknown) => void,
  ) => {
    if (error) {
      if (reject) return reject(error)
      throw error
    }
    return resolve(result)
  }
  return qb
}
