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
