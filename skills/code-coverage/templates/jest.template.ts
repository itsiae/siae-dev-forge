/**
 * Use this template ONLY when Phase 2 detects a pre-existing Jest config
 * (jest.config.ts|js, or "jest" in package.json scripts.test).
 * For all new JS/TS projects use vitest.template.ts instead.
 *
 * Replace all {{PLACEHOLDER}} tokens before use.
 */

import { {{ExportedFunction}}, {{ExportedClass}} } from '{{MODULE_IMPORT_PATH}}'
import { {{DepMethod}} } from '{{DEP_IMPORT_PATH}}'

jest.mock('{{DEP_IMPORT_PATH}}', () => ({
  {{DepMethod}}: jest.fn(),
}))

const mock{{DepMethod}} = {{DepMethod}} as jest.MockedFunction<typeof {{DepMethod}}>

describe('{{ExportedFunction}}', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('should {{HAPPY_PATH_DESCRIPTION}}', async () => {
    // Arrange
    mock{{DepMethod}}.mockResolvedValue({{DEP_RETURN_VALUE}})
    // Act
    const result = await {{ExportedFunction}}({{HAPPY_PATH_INPUT}})
    // Assert
    expect(result).toEqual({{EXPECTED_OUTPUT}})
    expect(mock{{DepMethod}}).toHaveBeenCalledWith({{DEP_EXPECTED_ARG}})
  })

  it('should {{EDGE_CASE_1_DESCRIPTION}} when input is empty', async () => {
    // Arrange
    mock{{DepMethod}}.mockResolvedValue({{EDGE_CASE_1_DEP_RETURN}})
    // Act
    const result = await {{ExportedFunction}}({{EDGE_CASE_1_INPUT}})
    // Assert
    expect(result).toEqual({{EDGE_CASE_1_EXPECTED}})
  })

  it('should {{EDGE_CASE_2_DESCRIPTION}} at boundary', async () => {
    // Arrange
    mock{{DepMethod}}.mockResolvedValue({{EDGE_CASE_2_DEP_RETURN}})
    // Act
    const result = await {{ExportedFunction}}({{EDGE_CASE_2_INPUT}})
    // Assert
    expect(result).toEqual({{EDGE_CASE_2_EXPECTED}})
  })

  it('should throw {{ERROR_TYPE}} when {{NEGATIVE_CONDITION}}', async () => {
    // Arrange
    mock{{DepMethod}}.mockRejectedValue(new {{ERROR_TYPE}}('{{ERROR_MESSAGE}}'))
    // Act & Assert
    await expect({{ExportedFunction}}({{INVALID_INPUT}})).rejects.toThrow('{{ERROR_MESSAGE}}')
  })
})

describe('{{ExportedClass}}', () => {
  let instance: {{ExportedClass}}

  beforeEach(() => {
    jest.clearAllMocks()
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

    it('should return null/default for missing input', async () => {
      // Act
      const result = await instance.{{methodName}}(undefined)
      // Assert
      expect(result).toBeNull()
    })

    it('should handle max-length string input', async () => {
      // Arrange
      const maxInput = 'x'.repeat({{MAX_LENGTH}})
      // Act + Assert
      await expect(instance.{{methodName}}(maxInput)).resolves.toBeDefined()
    })

    it('should throw when input is invalid', async () => {
      // Act & Assert
      await expect(instance.{{methodName}}({{INVALID_INPUT}})).rejects.toThrow({{ERROR_TYPE}})
    })
  })
})
