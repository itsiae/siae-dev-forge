import json
import boto3
import time
import os
from datetime import datetime, timezone

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]


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

    # Hive-style partitioned path
    now = datetime.now(timezone.utc)
    key = (
        f"devforge-logs/year={now.year}/month={now.month:02d}/day={now.day:02d}/"
        f"{dev_id}-{int(time.time())}.jsonl"
    )

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body,
        ContentType="application/jsonl",
    )

    return {"statusCode": 200, "body": json.dumps({"key": key})}
