# Functional bug report

- **Run id**: example-py-lambda
- **Scope hash**: 9e3b71c0
- **Skill semver**: 1.0.0
- **Model id**: claude-opus-4-7
- **Mode**: strict
- **Confidence (global)**: high
- **Findings**: 0 SEV-1 · 1 SEV-2 · 1 SEV-3 · 0 SEV-4
- **Lang**: en

## Index

| Finding | Journey | Severity | Title | Entry point |
|---|---|---|---|---|
| F-0001 | J-001 | SEV-2 | SQS-triggered Lambda lacks idempotency on retry | single:notifier/handlers/sqs_handler.py |
| F-0002 | J-002 | SEV-3 | API Gateway endpoint accepts unbounded user-id length | single:notifier/handlers/api_handler.py |

## Journey J-001 — Notification delivery

### F-0001 — SQS-triggered Lambda lacks idempotency on retry

- **Severity**: SEV-2 (rubric row R-SEV2-03)
- **Pattern**: BP-004
- **Entry point**: single:notifier/handlers/sqs_handler.py
- **Confidence**: high

**Preconditions**

- The SQS queue "notifications-prod" is configured with a redrive
  policy targeting "notifications-dlq" after 3 attempts.
- The Lambda function has no idempotency table configured.

**Steps**

1. (event-publisher) Publish message `{"user_id":"123","template":"welcome"}` to SQS queue "notifications-prod"
2. (event-publisher) Publish the same message to SQS queue "notifications-prod" within 1 second
3. (observer) Open the table "audit_notifications" on database "notifier-prod" and report the row count for user_id "123"

**Expected result**

Exactly one row is present in "audit_notifications" for user_id "123".

**Actual result**

Two rows are present in "audit_notifications" for user_id "123"; the
user receives the welcome email twice.

**Evidence**

- `handlers/sqs_handler.py:14-29` @ `8b2e4f0` (excerpt)
  > def handler(event, context):
- `handlers/sqs_handler.py:31-38` @ `8b2e4f0` (excerpt)
  > db.execute("INSERT INTO audit_notifications ...")
- `template.yaml:42-55` @ `8b2e4f0` (excerpt)
  > Events: { Sqs: { Type: SQS, Queue: !GetAtt NotificationsQueue.Arn } }

**Suggested fix direction**

Add a dedupe table keyed on `(user_id, template, sqs_message_id)` and
short-circuit the handler on a hit; alternatively, declare the side
effect as upsert on the same key.

**Reproduction rate target**

`>=95%`

**Boundary observations**

- single:notifier/handlers/sqs_handler.py → queue-name `notifications-prod` → terraform-hcl:infra/messaging

## Journey J-002 — Profile update

### F-0002 — API Gateway endpoint accepts unbounded user-id length

- **Severity**: SEV-3 (rubric row R-SEV3-04)
- **Pattern**: BP-001
- **Entry point**: single:notifier/handlers/api_handler.py
- **Confidence**: high

**Preconditions**

- The endpoint POST /v1/profile is publicly reachable.
- The request body is validated only for required keys, not for size.

**Steps**

1. (api-caller) Send HTTP POST /v1/profile with body `{"user_id":"<25000-char-string>","name":"x"}`
2. (observer) Inspect the response status code and report the body of the response
3. (observer) Open the CloudWatch log group "/aws/lambda/notifier-api" and report the entries with level=ERROR for the request id

**Expected result**

The response is `400 Bad Request` with a clear error naming the `user_id` length constraint.

**Actual result**

The Lambda returns `500 Internal Server Error`; the log group contains
a stack trace from the DynamoDB client refusing the oversized key.

**Evidence**

- `handlers/api_handler.py:18-27` @ `8b2e4f0` (excerpt)
  > body = json.loads(event["body"])
- `handlers/api_handler.py:30-35` @ `8b2e4f0` (excerpt)
  > table.put_item(Item={"user_id": body["user_id"], ...})

**Suggested fix direction**

Introduce a pydantic model with `constr(max_length=128)` for
`user_id` and reject malformed requests with a 422 response that
names the offending field.

**Reproduction rate target**

`>=95%`
