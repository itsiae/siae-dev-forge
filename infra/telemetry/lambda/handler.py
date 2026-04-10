import json
import re
import boto3
import time
import os
from datetime import datetime, timezone

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

# Allow-list: only safe chars for S3 keys, truncate to 64 chars
_SAFE_ID = re.compile(r"[^a-zA-Z0-9@._-]")


def _build_s3_key(body, now):
    """Build S3 key from JSONL body.

    Schema v2 (event_id + sid present): deterministic key so re-uploads
    overwrite the same object → idempotent dedup.
    Schema v1 (no event_id): timestamp-based key (legacy behaviour).
    """
    lines = [ln for ln in body.split("\n") if ln.strip()]

    # Parse first line for metadata
    try:
        first_line = json.loads(lines[0])
    except (json.JSONDecodeError, IndexError):
        first_line = {}

    dev_id = first_line.get("user", "unknown") if isinstance(first_line, dict) else "unknown"
    dev_id = _SAFE_ID.sub("_", dev_id)[:64] or "unknown"

    date_prefix = (
        f"devforge-logs/year={now.year}/month={now.month:02d}/day={now.day:02d}"
    )

    # Schema v2: deterministic key using sid + event_id range
    sid = first_line.get("sid") if isinstance(first_line, dict) else None
    first_event_id = first_line.get("event_id") if isinstance(first_line, dict) else None

    if sid and first_event_id:
        # Parse last line to get the ending event_id of the batch
        try:
            last_line = json.loads(lines[-1])
            last_event_id = last_line.get("event_id", first_event_id)
        except (json.JSONDecodeError, IndexError):
            last_event_id = first_event_id

        safe_sid = _SAFE_ID.sub("_", str(sid))[:64]
        safe_first = _SAFE_ID.sub("_", str(first_event_id))[:64]
        safe_last = _SAFE_ID.sub("_", str(last_event_id))[:64]

        return (
            f"{date_prefix}/sid-{safe_sid}/"
            f"batch-{safe_first}-to-{safe_last}.jsonl"
        )

    # Schema v1 fallback: non-deterministic key with timestamp
    return f"{date_prefix}/{dev_id}-{int(time.time())}.jsonl"


def handler(event, context):
    """Receive JSONL telemetry payload, validate, and store on S3."""
    body = event.get("body", "")
    if not body or len(body) > 1_048_576:  # 1 MB max
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid payload"})}

    now = datetime.now(timezone.utc)
    key = _build_s3_key(body, now)

    try:
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=body,
            ContentType="application/jsonl",
        )
    except Exception as e:
        print(json.dumps({"error": str(e), "key": key}))
        return {"statusCode": 502, "body": json.dumps({"error": "Storage failure"})}

    return {"statusCode": 200, "body": json.dumps({"key": key})}
