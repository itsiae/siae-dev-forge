"""Auto-detect data sources for dev analytics.

Matrice mode:
    github | s3_devforge | s3_blend | mode
    OK     | OK          | OK       | FULL
    OK     | OK          | KO       | HYBRID
    OK     | KO          | *        | GITHUB-ONLY
    KO     | *           | *        | ABORT
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Literal

Mode = Literal["FULL", "HYBRID", "GITHUB-ONLY", "ABORT"]

S3_BUCKET = "siae-devforge-telemetry"
S3_DEVFORGE_PREFIX = "devforge-logs/"
S3_BLEND_PREFIX = "blend-usage/"


@dataclass
class SourceReport:
    """Stato delle fonti rilevate."""
    github: bool
    s3_devforge: bool
    s3_blend: bool

    def mode(self) -> Mode:
        if not self.github:
            return "ABORT"
        if self.s3_devforge and self.s3_blend:
            return "FULL"
        if self.s3_devforge or self.s3_blend:
            return "HYBRID"
        return "GITHUB-ONLY"

    def as_dict(self) -> dict:
        return {
            "github": self.github,
            "s3_devforge": self.s3_devforge,
            "s3_blend": self.s3_blend,
            "mode": self.mode(),
        }


def check_gh_auth() -> bool:
    """True se `gh auth status` indica sessione attiva."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        stderr = result.stderr if isinstance(result.stderr, str) else ""
        return result.returncode == 0 and "Logged in" in (stdout + stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_s3_prefix(bucket: str, prefix: str) -> bool:
    """True se bucket/prefix è accessibile (head_bucket OK).

    Nota: non verifica la presenza di oggetti — quella è runtime concern
    delegata ai collector (graceful degrade se vuoto).
    """
    try:
        import boto3  # lazy import
        s3 = boto3.client("s3")
        s3.head_bucket(Bucket=bucket)
        return True
    except Exception:
        return False


def autodetect(abort_on_no_github: bool = True) -> SourceReport:
    """Rileva le fonti disponibili."""
    github = check_gh_auth()
    if not github and abort_on_no_github:
        raise RuntimeError(
            "GitHub CLI not authenticated. Run `gh auth login` and retry."
        )

    s3_devforge = check_s3_prefix(S3_BUCKET, S3_DEVFORGE_PREFIX) if github else False
    s3_blend = check_s3_prefix(S3_BUCKET, S3_BLEND_PREFIX) if github else False

    return SourceReport(
        github=github,
        s3_devforge=s3_devforge,
        s3_blend=s3_blend,
    )


if __name__ == "__main__":
    import json
    report = autodetect(abort_on_no_github=False)
    print(json.dumps(report.as_dict(), indent=2))
