/**
 * VITEST LAMBDA MODULE TEMPLATE
 * ====================================================================
 * Per moduli (services / utils / repositories) usati DENTRO i Lambda handler.
 * Equivalente al vitest.template.ts standard ma con AWS SDK mock pre-configurato.
 *
 * Mock pattern:
 * - aws-sdk-client-mock per AWS SDK v3 client (DynamoDB, S3, SQS, SNS)
 * - vi.mock per dipendenze interne (services collaborator)
 *
 * Replace all {{PLACEHOLDER}} tokens before use.
 * ====================================================================
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mockClient } from 'aws-sdk-client-mock'
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'

const ddbMock = mockClient(DynamoDBDocumentClient)

beforeEach(() => {
  vi.clearAllMocks()
  ddbMock.reset()
})

describe('{{SUT_NAME}}', () => {
  it('happy path — valid input returns expected output', async () => {
    // Arrange
    const input = {{HAPPY_INPUT}}
    const expected = {{HAPPY_OUTPUT}}

    // Act
    const result = await {{SUT_FUNCTION}}(input)

    // Assert
    expect(result).toEqual(expected)
  })

  it('edge case — boundary input handled correctly', async () => {
    expect(await {{SUT_FUNCTION}}({{EDGE_INPUT}})).toEqual({{EDGE_OUTPUT}})
  })

  it('negative path — throws on invalid input', async () => {
    await expect({{SUT_FUNCTION}}({{INVALID_INPUT}})).rejects.toThrow('{{ERROR_MESSAGE}}')
  })
})
