"""Integration tests for Lambda handler.py using moto mock AWS (PR-B).

Scope:
- payload limit 1MB -> 5MB
- dedup via DynamoDB PutItem with ConditionExpression (exactly-once)
- applicative DLQ via SQS send_message on storage failure
- structured response with stored/deduped counts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[3]
LAMBDA_DIR = REPO_ROOT / "infra" / "telemetry" / "lambda"
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))

BUCKET = "siae-devforge-telemetry"
DEDUP_TABLE = "devforge-event-dedup"
DLQ_NAME = "devforge-telemetry-dlq"


@pytest.fixture
def aws_env(monkeypatch):
    """Fixture: mock AWS services + set Lambda env vars + reload handler."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="eu-west-1")
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        ddb = boto3.client("dynamodb", region_name="eu-west-1")
        ddb.create_table(
            TableName=DEDUP_TABLE,
            KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        sqs = boto3.client("sqs", region_name="eu-west-1")
        q = sqs.create_queue(QueueName=DLQ_NAME)
        dlq_url = q["QueueUrl"]

        monkeypatch.setenv("BUCKET_NAME", BUCKET)
        monkeypatch.setenv("DEDUP_TABLE", DEDUP_TABLE)
        monkeypatch.setenv("DLQ_QUEUE_URL", dlq_url)
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

        # Fresh import after env + mocks are live
        for mod in ("handler",):
            if mod in sys.modules:
                del sys.modules[mod]
        import handler  # noqa: E402
        yield {"s3": s3, "ddb": ddb, "sqs": sqs, "dlq_url": dlq_url, "handler": handler}


def _event(body: str) -> dict:
    return {"body": body}


def test_happy_path_stores_payload_on_s3(aws_env):
    body = json.dumps(
        {"event_id": "sid1-1", "sid": "sid1", "user": "lodetomasi", "event": "test"}
    )
    res = aws_env["handler"].handler(_event(body), None)
    assert res["statusCode"] == 200
    parsed = json.loads(res["body"])
    assert parsed.get("stored", 0) == 1
    objs = aws_env["s3"].list_objects_v2(Bucket=BUCKET).get("Contents", [])
    assert len(objs) == 1


def test_payload_over_5mb_returns_400(aws_env):
    body = "x" * (5_242_881)
    res = aws_env["handler"].handler(_event(body), None)
    assert res["statusCode"] == 400


def test_dedup_same_event_id_twice_stores_once(aws_env):
    body = json.dumps(
        {"event_id": "sid2-42", "sid": "sid2", "user": "u", "event": "test"}
    )
    r1 = aws_env["handler"].handler(_event(body), None)
    r2 = aws_env["handler"].handler(_event(body), None)
    assert r1["statusCode"] == 200
    assert json.loads(r1["body"])["stored"] == 1
    assert r2["statusCode"] == 200
    p2 = json.loads(r2["body"])
    assert p2.get("stored", 0) == 0
    assert p2.get("deduped", 0) == 1 or p2.get("status") == "all_duplicates"


def test_dedup_different_events_both_stored(aws_env):
    b1 = json.dumps({"event_id": "sid3-1", "sid": "sid3", "user": "u", "event": "a"})
    b2 = json.dumps({"event_id": "sid3-2", "sid": "sid3", "user": "u", "event": "b"})
    r1 = aws_env["handler"].handler(_event(b1), None)
    r2 = aws_env["handler"].handler(_event(b2), None)
    assert json.loads(r1["body"])["stored"] == 1
    assert json.loads(r2["body"])["stored"] == 1


def test_dlq_receives_payload_on_s3_failure(aws_env, monkeypatch):
    body = json.dumps({"event_id": "sid4-1", "sid": "sid4", "user": "u", "event": "x"})
    handler = aws_env["handler"]

    def boom(*a, **k):
        raise RuntimeError("simulated S3 outage")

    monkeypatch.setattr(handler.s3, "put_object", boom)
    res = handler.handler(_event(body), None)
    assert res["statusCode"] == 502

    msgs = aws_env["sqs"].receive_message(
        QueueUrl=aws_env["dlq_url"], MaxNumberOfMessages=10
    )
    assert "Messages" in msgs and len(msgs["Messages"]) >= 1
    assert body in msgs["Messages"][0]["Body"]


def test_multi_line_jsonl_deduplicates_per_event(aws_env):
    first = "\n".join(
        [
            json.dumps({"event_id": "sid5-1", "sid": "sid5", "user": "u", "event": "a"}),
            json.dumps({"event_id": "sid5-2", "sid": "sid5", "user": "u", "event": "b"}),
        ]
    )
    r1 = aws_env["handler"].handler(_event(first), None)
    assert json.loads(r1["body"])["stored"] == 2

    second = "\n".join(
        [
            json.dumps({"event_id": "sid5-1", "sid": "sid5", "user": "u", "event": "a"}),
            json.dumps({"event_id": "sid5-3", "sid": "sid5", "user": "u", "event": "c"}),
        ]
    )
    r2 = aws_env["handler"].handler(_event(second), None)
    parsed = json.loads(r2["body"])
    assert parsed.get("stored", 0) == 1
    assert parsed.get("deduped", 0) == 1
