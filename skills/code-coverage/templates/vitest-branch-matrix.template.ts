/**
 * VITEST BRANCH-MATRIX TEMPLATE
 * ====================================================================
 * Usato quando coverage_mode == "branch-priority" (vedi classify_coverage_mode.py).
 * Per OGNI operatore di fallback (?? / || / && / ?:) trovato nel source-under-test
 * genera 3 test: ramo null, ramo undefined, ramo present.
 * Placeholder {{CLASS_MOCK_BLOCK}} e {{TZ_MOCK_BLOCK}} sostituiti dai task WS-3.
 * ====================================================================
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_EXPORTS}} } from '{{SUT_PATH}}'
// {{CLASS_MOCK_BLOCK}}
// {{TZ_MOCK_BLOCK}}

describe('{{SUT_NAME}} — branch matrix', () => {
  beforeEach(() => { vi.clearAllMocks() })

  // ── Ripeti questo describe() per OGNI operatore trovato da count_branch_operators.py
  describe('{{FIELD_NAME}} fallback branch', () => {
    it('returns fallback when {{FIELD_NAME}} is null', () => {
      const fixture = { ...{{BASE_FIXTURE}}, {{FIELD_NAME}}: null }
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{FALLBACK_VALUE}})
    })

    it('returns fallback when {{FIELD_NAME}} is undefined', () => {
      const fixture = { ...{{BASE_FIXTURE}} }
      delete (fixture as Record<string, unknown>).{{FIELD_NAME}}
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{FALLBACK_VALUE}})
    })

    it('returns value when {{FIELD_NAME}} is present', () => {
      const fixture = { ...{{BASE_FIXTURE}}, {{FIELD_NAME}}: {{SAMPLE_VALUE}} }
      const result = {{SUT_FUNCTION}}(fixture)
      expect(result.{{OUTPUT_FIELD}}).toBe({{SAMPLE_VALUE}})
    })
  })

  // ── Dual-fixture (solo se branch_operator_count > 40)
  // {{DUAL_FIXTURE_BLOCK}} es:
  //   const minimalFixture = {}
  //   const fullFixture = { /* TUTTI i campi opzionali valorizzati */ }
  //   it('with all optional fields populated', () => {
  //     expect({{SUT_FUNCTION}}(fullFixture)).toMatchObject({ /* valori attesi */ })
  //   })
})
