/**
 * Use this template for: React, Next.js, Vue, Nuxt, Angular, Svelte, Remix, Astro,
 * Node.js (Express/NestJS/Fastify/Koa/Hapi).
 * For Serverless/Lambda stacks use vitest-lambda.template.ts instead.
 * Vitest is the default for ALL non-Lambda JS/TS stacks. Prefer over jest.template.ts unless
 * a pre-existing Jest config is detected in Phase 2.
 *
 * Replace all {{PLACEHOLDER}} tokens before use.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { MockedFunction } from 'vitest'

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
