import { vi } from 'vitest'
/** Crea un mock di classe: vi.fn().mockImplementation con i metodi richiesti. */
export function mockClass(methods: string[], impl: Record<string, unknown> = {}) {
  return vi.fn().mockImplementation(() => {
    const inst: Record<string, unknown> = {}
    for (const m of methods) inst[m] = impl[m] ?? vi.fn()
    return inst
  })
}
