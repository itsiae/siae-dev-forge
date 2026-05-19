"""SAFE: presigned URL con TTL <=60s (raccomandazione ADR-008)."""
import boto3


def make_url_safe(key: str) -> str:
    s3 = boto3.client("s3")
    # SAFE: TTL 60s
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": "bucket", "Key": key},
        ExpiresIn=60,
    )
