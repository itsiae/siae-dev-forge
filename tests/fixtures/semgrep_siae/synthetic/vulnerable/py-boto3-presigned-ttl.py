"""Wave 3 cross-stack porting: Python boto3 generate_presigned_url con TTL >3600s.
Synthetic minimal repro (CWE-200), no broadcasting code.
"""
import boto3


def make_url_vulnerable(key: str) -> str:
    s3 = boto3.client("s3")
    # VULNERABLE: TTL 24h (86400s) — URL "vendibile" per giorni
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": "bucket", "Key": key},
        ExpiresIn=86400,
    )


def make_url_vulnerable2(key: str) -> str:
    s3 = boto3.client("s3")
    # VULNERABLE: TTL 1h (3600s) — minimum threshold superato
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": "bucket", "Key": key},
        ExpiresIn=3600,
    )
