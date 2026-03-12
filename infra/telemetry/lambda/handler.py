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


def handler(event, context):
    """Receive JSONL telemetry payload, validate, and store on S3."""
    body = event.get("body", "")
    if not body or len(body) > 1_048_576:  # 1 MB max
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid payload"})}

    # Extract dev-id from first JSONL line
    try:
        first_line = json.loads(body.split("\n")[0])
        dev_id = first_line.get("user", "unknown")
    except (json.JSONDecodeError, IndexError):
        dev_id = "unknown"

    # Sanitize dev_id — prevent path traversal and invalid S3 key chars
    dev_id = _SAFE_ID.sub("_", dev_id)[:64] or "unknown"

    # Hive-style partitioned path
    now = datetime.now(timezone.utc)
    key = (
        f"devforge-logs/year={now.year}/month={now.month:02d}/day={now.day:02d}/"
        f"{dev_id}-{int(time.time())}.jsonl"
    )

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
