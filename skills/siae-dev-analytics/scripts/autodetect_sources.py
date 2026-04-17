"""Auto-detect data sources for dev analytics.

Matrice mode:
    github | s3_devforge | s3_blend | mode
    OK     | OK          | OK       | FULL
    OK     | OK          | KO       | HYBRID
    OK     | KO          | *        | GITHUB-ONLY
    KO     | *           | *        | ABORT
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
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
    aws_profile: bool = False
    anthropic_api: bool = False

    def mode(self) -> Mode:
        """Mode coerente con design matrix §4.

        github=OK + s3_devforge=OK + s3_blend=OK → FULL
        github=OK + s3_devforge=OK + s3_blend=KO → HYBRID
        github=OK + s3_devforge=KO + s3_blend=* → GITHUB-ONLY
        github=KO → ABORT

        s3_blend-only senza s3_devforge ricade in GITHUB-ONLY: senza
        telemetry events non c'è accuracy superior su Q4 verification_rate,
        quindi la presenza di blend-usage sola non giustifica HYBRID.
        """
        if not self.github:
            return "ABORT"
        if self.s3_devforge and self.s3_blend:
            return "FULL"
        if self.s3_devforge:
            return "HYBRID"
        return "GITHUB-ONLY"

    def as_dict(self) -> dict:
        return {
            "github": self.github,
            "s3_devforge": self.s3_devforge,
            "s3_blend": self.s3_blend,
            "aws_profile": self.aws_profile,
            "anthropic_api": self.anthropic_api,
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


def check_aws_profile() -> tuple[bool, str]:
    """Returns (available, reason)."""
    profile = os.getenv("AWS_PROFILE")
    if not profile:
        return False, "AWS_PROFILE non settato. Esegui: export AWS_PROFILE=siae-dev-forge"
    return True, f"AWS_PROFILE={profile}"


def check_anthropic_api() -> tuple[bool, str]:
    """Returns (available, reason)."""
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    if not has_key:
        return False, "ANTHROPIC_API_KEY mancante. Configura env var per abilitare cost fallback."
    return True, "ANTHROPIC_API_KEY presente"


def autodetect(abort_on_no_github: bool = True) -> SourceReport:
    """Rileva le fonti disponibili."""
    github = check_gh_auth()
    if not github and abort_on_no_github:
        raise RuntimeError(
            "GitHub CLI not authenticated. Run `gh auth login` and retry."
        )

    s3_devforge = check_s3_prefix(S3_BUCKET, S3_DEVFORGE_PREFIX) if github else False
    s3_blend = check_s3_prefix(S3_BUCKET, S3_BLEND_PREFIX) if github else False

    aws_ok, _ = check_aws_profile()
    anthropic_ok, _ = check_anthropic_api()

    return SourceReport(
        github=github,
        s3_devforge=s3_devforge,
        s3_blend=s3_blend,
        aws_profile=aws_ok,
        anthropic_api=anthropic_ok,
    )


if __name__ == "__main__":
    import json
    report = autodetect(abort_on_no_github=False)
    print(json.dumps(report.as_dict(), indent=2))
