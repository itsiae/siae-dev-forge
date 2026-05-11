import { describe, it, expect, vi } from 'vitest'
import { format } from '@/utils/format'

vi.mock('@/utils/helpers', () => ({ helper: vi.fn() }))

describe('format', () => {
  it('works', () => expect(format(1)).toBe('1'))
})
