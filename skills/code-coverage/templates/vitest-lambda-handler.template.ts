/**
 * VITEST LAMBDA HANDLER TEMPLATE
 * ====================================================================
 * Per file: src/handlers/*.ts che esportano un Lambda handler
 * (APIGatewayProxyHandler, SQSHandler, SNSHandler, EventBridgeHandler, etc.)
 *
 * Mock pattern:
 * - aws-sdk-client-mock per AWS SDK v3 (preferito)
 * - Event mocks per ogni source: APIGateway / SQS / SNS / EventBridge / DynamoDB / S3
 *
 * Replace all {{PLACEHOLDER}} tokens before use.
 * ====================================================================
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import type { APIGatewayProxyEvent, Context } from 'aws-lambda'
import { mockClient } from 'aws-sdk-client-mock'
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb'
import { handler } from './{{HANDLER_FILE_NAME}}'

const ddbMock = mockClient(DynamoDBDocumentClient)

const MOCK_CONTEXT: Context = {
  callbackWaitsForEmptyEventLoop: false,
  functionName: '{{HANDLER_NAME}}',
  functionVersion: '$LATEST',
  invokedFunctionArn: 'arn:aws:lambda:eu-west-1:000000000000:function:{{HANDLER_NAME}}',
  memoryLimitInMB: '128',
  awsRequestId: 'test-request-id',
  logGroupName: '/aws/lambda/{{HANDLER_NAME}}',
  logStreamName: '2026/01/01/[$LATEST]00000',
  getRemainingTimeInMillis: () => 1000,
  done: () => {},
  fail: () => {},
  succeed: () => {},
}

beforeEach(() => {
  vi.clearAllMocks()
  ddbMock.reset()
})

describe('{{HANDLER_NAME}} Lambda handler', () => {
  it('returns 200 on valid input', async () => {
    // Arrange
    ddbMock.on(GetCommand).resolves({ Item: { id: '1', name: 'test' } })
    const event: Partial<APIGatewayProxyEvent> = {
      httpMethod: 'GET',
      path: '/resource/1',
      pathParameters: { id: '1' },
      headers: { 'Content-Type': 'application/json' },
      body: null,
      isBase64Encoded: false,
    }

    // Act
    const result = await handler(event as APIGatewayProxyEvent, MOCK_CONTEXT, () => {})

    // Assert
    expect(result.statusCode).toBe(200)
    expect(JSON.parse(result.body)).toMatchObject({ id: '1' })
  })

  it('returns 400 on missing required field', async () => {
    const event: Partial<APIGatewayProxyEvent> = {
      httpMethod: 'POST',
      body: JSON.stringify({}),
    }
    const result = await handler(event as APIGatewayProxyEvent, MOCK_CONTEXT, () => {})
    expect(result.statusCode).toBe(400)
  })

  it('returns 500 when downstream fails', async () => {
    ddbMock.on(GetCommand).rejects(new Error('DynamoDB unavailable'))
    const event: Partial<APIGatewayProxyEvent> = { httpMethod: 'GET', pathParameters: { id: '1' } }
    const result = await handler(event as APIGatewayProxyEvent, MOCK_CONTEXT, () => {})
    expect(result.statusCode).toBe(500)
  })
})
