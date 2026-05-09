/**
 * Use this template for: Serverless (Lambda/SST/SAM/CDK) stacks ONLY.
 * Contains API Gateway, SQS, SNS event mocks and aws-sdk-client-mock patterns.
 * For non-Lambda JS/TS projects use vitest.template.ts instead.
 *
 * ⚠️  THIS FILE HAS TWO MUTUALLY EXCLUSIVE SECTIONS:
 *   SECTION A (lines after this header, up to the Lambda Handler divider):
 *     Generic module/class tests — use for non-handler exports in a Lambda package.
 *   SECTION B (from "// ─── Lambda Handler" divider to end of file):
 *     Lambda handler tests with API Gateway, SQS, SNS event mocks.
 *
 *   USE ONLY ONE SECTION PER GENERATED TEST FILE.
 *   Copying both sections into a single file produces duplicate `import` declarations
 *   and `Cannot redeclare block-scoped variable` TypeScript errors.
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

describe('{{ExportedFunction}}', () => {
  beforeEach(() => { vi.clearAllMocks() })
  afterEach(() => { vi.restoreAllMocks() })

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

// ─── Lambda Handler ───────────────────────────────────────────────────────────

import type { APIGatewayProxyEvent, APIGatewayProxyResult, Context, SQSEvent, SNSEvent } from 'aws-lambda'
import { mockClient } from 'aws-sdk-client-mock'
import { DynamoDBDocumentClient, GetCommand, PutCommand } from '@aws-sdk/lib-dynamodb'
import { S3Client } from '@aws-sdk/client-s3'
import { handler } from '{{LAMBDA_HANDLER_IMPORT_PATH}}'

const ddbMock = mockClient(DynamoDBDocumentClient)
const s3Mock = mockClient(S3Client)
const mockContext = {} as Context

const baseEvent: Partial<APIGatewayProxyEvent> = {
  httpMethod: '{{HTTP_METHOD}}',
  path: '{{PATH}}',
  pathParameters: {{PATH_PARAMETERS}},
  queryStringParameters: null,
  headers: { 'Content-Type': 'application/json' },
  body: null,
  isBase64Encoded: false,
}

describe('Lambda: {{LAMBDA_FUNCTION_NAME}}', () => {
  beforeEach(() => { ddbMock.reset(); s3Mock.reset(); vi.clearAllMocks() })

  it('should return 200 for valid request', async () => {
    // Arrange
    ddbMock.on(GetCommand).resolves({ Item: {{DDB_ITEM}} })
    const event = { ...baseEvent, body: JSON.stringify({{REQUEST_BODY}}) } as APIGatewayProxyEvent
    // Act
    const result: APIGatewayProxyResult = await handler(event, mockContext)
    // Assert
    expect(result.statusCode).toBe(200)
    expect(JSON.parse(result.body)).toMatchObject({{EXPECTED_RESPONSE_BODY}})
  })

  it('should return 404 when DynamoDB item not found', async () => {
    // Arrange
    ddbMock.on(GetCommand).resolves({ Item: undefined })
    // Act
    const result = await handler({ ...baseEvent } as APIGatewayProxyEvent, mockContext)
    // Assert
    expect(result.statusCode).toBe(404)
  })

  it('should return 400 when body is malformed JSON', async () => {
    // Arrange + Act
    const result = await handler({ ...baseEvent, body: 'invalid' } as APIGatewayProxyEvent, mockContext)
    // Assert
    expect(result.statusCode).toBe(400)
  })

  it('should return 500 when DynamoDB throws', async () => {
    // Arrange
    ddbMock.on(GetCommand).rejects(new Error('DynamoDB unavailable'))
    // Act
    const result = await handler({ ...baseEvent } as APIGatewayProxyEvent, mockContext)
    // Assert
    expect(result.statusCode).toBe(500)
  })
})

// ─── Additional Event Type Skeletons ─────────────────────────────────────────
// Copy the describe block below into a NEW test file for SQS/SNS handlers.
// Do NOT add these to the Lambda Handler describe above — keep one handler per file.

/*
describe('SQS handler: {{SQS_HANDLER_FUNCTION_NAME}}', () => {
  beforeEach(() => { ddbMock.reset(); vi.clearAllMocks() })

  it('should process SQS message successfully', async () => {
    // Arrange
    const sqsEvent: SQSEvent = {
      Records: [{
        messageId: 'msg-1', receiptHandle: 'handle',
        body: JSON.stringify({{SQS_MESSAGE_BODY}}),
        attributes: {} as never, messageAttributes: {}, md5OfBody: '',
        eventSource: 'aws:sqs',
        eventSourceARN: 'arn:aws:sqs:us-east-1:123456789:{{QUEUE_NAME}}',
        awsRegion: 'us-east-1',
      }],
    }
    // Act
    await {{SQS_HANDLER_FUNCTION_NAME}}(sqsEvent, mockContext)
    // Assert
    expect(ddbMock.calls()).toHaveLength(1)
  })
})

describe('SNS handler: {{SNS_HANDLER_FUNCTION_NAME}}', () => {
  beforeEach(() => { ddbMock.reset(); vi.clearAllMocks() })

  it('should process SNS notification successfully', async () => {
    // Arrange
    const snsEvent: SNSEvent = {
      Records: [{
        EventSource: 'aws:sns', EventVersion: '1.0',
        EventSubscriptionArn: 'arn:aws:sns:us-east-1:123456789:{{TOPIC_NAME}}',
        Sns: {
          Type: 'Notification', MessageId: 'msg-1', TopicArn: 'arn:...',
          Subject: '', Message: JSON.stringify({{SNS_MESSAGE_BODY}}),
          Timestamp: new Date().toISOString(), SignatureVersion: '1',
          Signature: '', SigningCertUrl: '', UnsubscribeUrl: '',
          MessageAttributes: {},
        },
      }],
    }
    // Act
    await {{SNS_HANDLER_FUNCTION_NAME}}(snsEvent, mockContext)
    // Assert
    expect(ddbMock.calls()).toHaveLength(1)
  })
})
*/
