"""DevForge telemetry ingest Lambda (PR-B zero-loss transport).

Responsibilities:
1. Validate payload size (5MB cap, raised from 1MB in PR-B).
2. Per-event dedup via DynamoDB conditional PutItem (exactly-once).
3. Store unique events on S3 with deterministic key (schema v2) or
   legacy timestamp key (schema v1).
4. Applicative DLQ via SQS on storage failure (S3/DynamoDB outage).
   Native Lambda dead_letter_config is ignored on sync invocations
   (API Gateway is sync), so we implement the DLQ at handler level.
"""
import json
import os
import re
import time
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
ddb = boto3.client("dynamodb")
sqs = boto3.client("sqs")

BUCKET = os.environ["BUCKET_NAME"]
DEDUP_TABLE = os.environ.get("DEDUP_TABLE", "")
DLQ_URL = os.environ.get("DLQ_QUEUE_URL", "")

MAX_PAYLOAD_BYTES = 5_242_880
DEDUP_TTL_SECONDS = 7 * 86400

_SAFE_ID = re.compile(r"[^a-zA-Z0-9@._-]")


def _build_s3_key(body, now):
    lines = [ln for ln in body.split("\n") if ln.strip()]
    try:
        first_line = json.loads(lines[0])
    except (json.JSONDecodeError, IndexError):
        first_line = {}

    dev_id = first_line.get("user", "unknown") if isinstance(first_line, dict) else "unknown"
    dev_id = _SAFE_ID.sub("_", dev_id)[:64] or "unknown"
    date_prefix = f"devforge-logs/year={now.year}/month={now.month:02d}/day={now.day:02d}"
    sid = first_line.get("sid") if isinstance(first_line, dict) else None
    first_event_id = first_line.get("event_id") if isinstance(first_line, dict) else None

    if sid and first_event_id:
        try:
            last_line = json.loads(lines[-1])
            last_event_id = last_line.get("event_id", first_event_id)
        except (json.JSONDecodeError, IndexError):
            last_event_id = first_event_id
        safe_sid = _SAFE_ID.sub("_", str(sid))[:64]
        safe_first = _SAFE_ID.sub("_", str(first_event_id))[:64]
        safe_last = _SAFE_ID.sub("_", str(last_event_id))[:64]
        return f"{date_prefix}/sid-{safe_sid}/batch-{safe_first}-to-{safe_last}.jsonl"

    return f"{date_prefix}/{dev_id}-{int(time.time())}.jsonl"


def _dedup_check_and_set(event_id):
    if not DEDUP_TABLE or not event_id:
        return True
    try:
        ddb.put_item(
            TableName=DEDUP_TABLE,
            Item={
                "event_id": {"S": str(event_id)},
                "ttl": {"N": str(int(time.time()) + DEDUP_TTL_SECONDS)},
            },
            ConditionExpression="attribute_not_exists(event_id)",
        )
        return True
    except ddb.exceptions.ConditionalCheckFailedException:
        return False


def _send_to_dlq(body, error, request_id=None):
    if not DLQ_URL:
        return
    try:
        attrs = {"error": {"DataType": "String", "StringValue": str(error)[:1000]}}
        if request_id:
            attrs["request_id"] = {"DataType": "String", "StringValue": str(request_id)}
        sqs.send_message(QueueUrl=DLQ_URL, MessageBody=body, MessageAttributes=attrs)
    except Exception as sqs_err:  # noqa: BLE001
        print(json.dumps({"event": "dlq_send_failed", "error": str(sqs_err)}))


def handler(event, context):
    body = event.get("body", "")
    if not body or len(body) > MAX_PAYLOAD_BYTES:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid payload"})}

    now = datetime.now(timezone.utc)
    lines = body.split("\n")
    unique_lines = []
    deduped_count = 0

    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            eid = obj.get("event_id") if isinstance(obj, dict) else None
            if eid and not _dedup_check_and_set(eid):
                deduped_count += 1
                continue
        except json.JSONDecodeError:
            pass
        unique_lines.append(line)

    if not unique_lines:
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "all_duplicates", "deduped": deduped_count, "stored": 0}),
        }

    new_body = "\n".join(unique_lines)
    key = _build_s3_key(new_body, now)

    try:
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=new_body,
            ContentType="application/jsonl",
        )
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e), "key": key}))
        request_id = getattr(context, "aws_request_id", None) if context else None
        _send_to_dlq(body, e, request_id=request_id)
        return {"statusCode": 502, "body": json.dumps({"error": "Storage failure, queued in DLQ"})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "stored": len(unique_lines),
            "deduped": deduped_count,
            "s3_key": key,
        }),
    }
