/**
 * VITEST TEMPLATE — Mock pattern rationale
 * ====================================================================
 * vi.mock(path, factory) sostituisce il modulo per TUTTI i test del file.
 *   - Named exports:   ({ funcName: vi.fn() })
 *   - Default exports: ({ default: vi.fn() })  // chiave 'default' è critica
 *   - Misti:           ({ default: vi.fn(), helper: vi.fn() })
 * Verify export shape FIRST via grep:
 *   grep -nE "^export (default|const|function|class)" <dep-source-file>
 * ====================================================================
 *
 * Use this template for: React, Next.js, Vue, Nuxt, Angular, Svelte, Remix, Astro,
 * Node.js (Express/NestJS/Fastify/Koa/Hapi).
 * For Serverless/Lambda handlers use vitest-lambda-handler.template.ts;
 * for Lambda internal modules use vitest-lambda-module.template.ts.
 * Vitest is the default for ALL non-Lambda JS/TS stacks. Prefer over jest.template.ts unless
 * a pre-existing Jest config is detected in Phase 2.
 *
 * Replace all {{PLACEHOLDER}} tokens before use.
 *
 * C1 fix — Placeholder cleanup (HIGH severity)
 * ====================================================================
 * Quando un SUT esporta SOLO `foo` (no class), il placeholder
 * `{{ExportedClass}}` resta vuoto post-sostituzione e produce
 * `import { foo,  }` → SyntaxError → 1 iter Phase 7 sprecata.
 *
 * Soluzione: dopo aver fatto le sostituzioni `{{...}}` → valore,
 * SEMPRE eseguire lo script `clean_template_placeholders` di
 * `lib/template-cache.sh` (o equivalente) che applica:
 *   1. Rimuove `, {{...}}` con pattern vuoto
 *   2. Pulisce trailing comma in import lines: `, }` → ` }`
 *   3. Pulisce leading comma: `{ ,` → `{ `
 *   4. Collassa import vuoto: `import { } from '...'` → riga rimossa
 *   5. Idem per export simbolo singolo: `import { foo, } from` → `import { foo } from`
 *
 * Pattern marker `__OPTIONAL_SYMBOL__` (vedi sotto): se un placeholder
 * potrebbe essere vuoto, prefissare con questo marker. Il cleanup script
 * rimuove il segmento intero `__OPTIONAL_SYMBOL__:<token>` se il token
 * è vuoto, oppure mantiene `<token>` se è valorizzato.
 * ====================================================================
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { MockedFunction } from 'vitest'

// IMPORT_VARIANT: cleanup_template_placeholders sostituirà {{ExportedClass}}
// vuoto e pulirà trailing comma. Se {{ExportedClass}} valorizzato, resta named.
import { {{ExportedFunction}}, {{ExportedClass}} } from '{{MODULE_IMPORT_PATH}}'
import { {{DepMethod}} } from '{{DEP_IMPORT_PATH}}'

vi.mock('{{DEP_IMPORT_PATH}}', () => ({
  {{DepMethod}}: vi.fn(),
}))

const mock{{DepMethod}} = {{DepMethod}} as MockedFunction<typeof {{DepMethod}}>

// Mock cleanup strategy:
// - DEFAULT: vi.clearAllMocks() in beforeEach (resetta calls/instances)
// - Aggiungi afterEach(vi.restoreAllMocks()) SOLO se il file usa vi.spyOn()
//   (non necessario se usi solo vi.mock()/vi.fn())
describe('{{ExportedFunction}}', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('should {{HAPPY_PATH_DESCRIPTION}}', async () => {
    // Arrange
    const input = {{HAPPY_PATH_INPUT}}
    const expectedOutput = {{EXPECTED_OUTPUT}}
    mock{{DepMethod}}.mockResolvedValue({{DEP_RETURN_VALUE}})

    // Act
    const result = await {{ExportedFunction}}(input)

    // Assert
    expect(result).toEqual(expectedOutput)
    expect(mock{{DepMethod}}).toHaveBeenCalledWith({{DEP_EXPECTED_ARG}})
    expect(mock{{DepMethod}}).toHaveBeenCalledTimes(1)
  })

  it('should {{EDGE_CASE_1_DESCRIPTION}} when input is empty', async () => {
    // Arrange
    const emptyInput = {{EDGE_CASE_1_INPUT}}
    mock{{DepMethod}}.mockResolvedValue({{EDGE_CASE_1_DEP_RETURN}})

    // Act
    const result = await {{ExportedFunction}}(emptyInput)

    // Assert
    expect(result).toEqual({{EDGE_CASE_1_EXPECTED}})
  })

  it('should {{EDGE_CASE_2_DESCRIPTION}} when called concurrently', async () => {
    // Arrange
    mock{{DepMethod}}
      .mockResolvedValueOnce({{DEP_RETURN_1}})
      .mockResolvedValueOnce({{DEP_RETURN_2}})

    // Act
    const [result1, result2] = await Promise.all([
      {{ExportedFunction}}({{EDGE_CASE_2_INPUT_1}}),
      {{ExportedFunction}}({{EDGE_CASE_2_INPUT_2}}),
    ])

    // Assert
    expect(result1).toEqual({{EXPECTED_1}})
    expect(result2).toEqual({{EXPECTED_2}})
  })

  it('should throw {{ERROR_TYPE}} when {{NEGATIVE_CONDITION}}', async () => {
    // Arrange
    mock{{DepMethod}}.mockRejectedValue(new {{ERROR_TYPE}}('{{ERROR_MESSAGE}}'))

    // Act & Assert
    await expect({{ExportedFunction}}({{INVALID_INPUT}})).rejects.toThrow({{ERROR_TYPE}})
  })
})

describe('{{ExportedClass}}', () => {
  let instance: {{ExportedClass}}

  beforeEach(() => {
    vi.clearAllMocks()
    instance = new {{ExportedClass}}({{CONSTRUCTOR_ARGS}})
  })

  describe('{{methodName}}', () => {
    it('should {{HAPPY_PATH_DESCRIPTION}}', async () => {
      // Arrange
      const input = {{HAPPY_PATH_INPUT}}
      // Act
      const result = await instance.{{methodName}}(input)
      // Assert
      expect(result).toEqual({{EXPECTED_OUTPUT}})
    })

    it('should return default when input is null', async () => {
      // Arrange
      // Act
      const result = await instance.{{methodName}}(null)
      // Assert
      expect(result).toEqual({{NULL_DEFAULT_EXPECTED}})
    })

    it('should handle maximum boundary value', async () => {
      // Arrange
      const maxInput = {{MAX_BOUNDARY_INPUT}}
      // Act
      const result = await instance.{{methodName}}(maxInput)
      // Assert
      expect(result).toBeDefined()
    })

    it('should throw {{ERROR_TYPE}} when input fails validation', async () => {
      // Arrange + Act + Assert
      await expect(instance.{{methodName}}({{INVALID_INPUT}})).rejects.toThrow({{ERROR_TYPE}})
    })
  })
})

// ====================================================================
// VITEST TEMPLATE — Variants (P8 deterministic mock shape)
// ====================================================================
// Selezionare UNA variante in base al numero di dependencies del SUT.
// Cancellare le altre prima di scrivere il test file finale.
// ====================================================================

// --- VARIANT_NO_DEPS ------------------------------------------------
// T1 Pure Logic: 0 imports esterni, 0 mock necessari.
// import { describe, it, expect, beforeEach, vi } from 'vitest'
// import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'
// beforeEach(() => { vi.clearAllMocks() })
// describe('{{SUT_NAME}}', () => { /* tests */ })

// --- VARIANT_SINGLE_DEP ---------------------------------------------
// 1 dependency, named export (mock factory single shape).
// import { describe, it, expect, beforeEach, vi } from 'vitest'
// import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'
// import { {{DEP_NAMED_EXPORT}} } from '{{DEP_IMPORT_PATH}}'
// vi.mock('{{DEP_IMPORT_PATH}}', () => ({ {{DEP_NAMED_EXPORT}}: vi.fn() }))
// beforeEach(() => { vi.clearAllMocks() })

// --- VARIANT_TWO_DEPS -----------------------------------------------
// 2 dependencies (mixed default/named exports).
// vi.mock('{{DEP1_IMPORT_PATH}}', () => ({ default: vi.fn() }))
// vi.mock('{{DEP2_IMPORT_PATH}}', () => ({ {{DEP2_NAMED}}: vi.fn() }))

// --- VARIANT_MULTI_DEPS ---------------------------------------------
// 3+ dependencies (T3/T4 service heavy). Auto-generated per dep:
// vi.mock('{{DEP1_IMPORT_PATH}}', () => ({ {{DEP1_EXPORTS}} }))
// vi.mock('{{DEP2_IMPORT_PATH}}', () => ({ {{DEP2_EXPORTS}} }))
// vi.mock('{{DEP3_IMPORT_PATH}}', () => ({ {{DEP3_EXPORTS}} }))
// Per >5 deps considera fixture/factory helper esterno.
