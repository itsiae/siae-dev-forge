"""Tests for ``lib.review_evidence.baseline_cache``.

Covers the 5 acceptance scenarios from Task 09:

1. ``baseline_key`` shape.
2. S3 cache miss → ``None``.
3. S3 store + fetch roundtrip.
4. D2 fallback: ``NoCredentialsError`` → local file is read instead.
5. A2 force-push detection via ``sha_exists_in_repo``.
"""
from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import boto3
from moto import mock_aws

from lib.review_evidence.baseline_cache import (
    BaselineCache,
    baseline_key,
    fetch_baseline,
    sha_exists_in_repo,
    store_baseline,
)
from lib.review_evidence.schema import ScoreCard


S3_BUCKET = "itsiae-review-evidence-baseline-prod"
S3_REGION = "eu-west-1"


def _make_scorecard(security: float = 80.0) -> ScoreCard:
    """Build a minimal ScoreCard with sane defaults for round-trip tests."""
    return ScoreCard(
        security=security,
        quality=70.0,
        coverage=65.0,
        spec_compliance=85.0,
        discipline=90.0,
        overall=78.0,
        weights_used={
            "security": 0.30,
            "quality": 0.20,
            "coverage": 0.20,
            "spec_compliance": 0.15,
            "discipline": 0.15,
        },
        missing_components=[],
    )


def _create_bucket() -> None:
    """Create the baseline bucket inside the active moto S3 mock."""
    boto3.client("s3", region_name=S3_REGION).create_bucket(
        Bucket=S3_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": S3_REGION},
    )


# ---------------------------------------------------------------------------
# 1. baseline_key shape (A1 contract — key is sha, no TTL)
# ---------------------------------------------------------------------------


def test_baseline_key_format():
    """Key shape is ``<repo_full_name>/<sha>.json`` exactly — IAM relies on it."""
    assert (
        baseline_key("itsiae/siae-dev-forge", "abc123")
        == "itsiae/siae-dev-forge/abc123.json"
    )


# ---------------------------------------------------------------------------
# 2. S3 cache miss → None
# ---------------------------------------------------------------------------


@mock_aws
def test_fetch_baseline_cache_miss_returns_none(tmp_path, monkeypatch):
    """NoSuchKey on S3 must not crash; with no local file either → ``None``."""
    # Redirect the local fallback into the tmp sandbox so we don't accidentally
    # hit the developer's real ``~/.claude`` directory during the test.
    monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", str(tmp_path / "fallback"))
    _create_bucket()

    result = fetch_baseline("itsiae/foo", "missingsha")

    assert result is None


# ---------------------------------------------------------------------------
# 3. S3 store + fetch roundtrip (D3+D5: S3 is the canonical store)
# ---------------------------------------------------------------------------


@mock_aws
def test_store_then_fetch_roundtrip():
    """Write a baseline to mocked S3 and read it back — values must survive."""
    _create_bucket()

    original = _make_scorecard(security=85.0)
    assert store_baseline("itsiae/foo", "abc123", original) is True

    fetched = fetch_baseline("itsiae/foo", "abc123")

    assert fetched is not None
    assert fetched.security == 85.0
    assert fetched.overall == 78.0
    assert fetched.weights_used["security"] == 0.30


# ---------------------------------------------------------------------------
# 4. D2 fallback: NoCredentialsError → local file
# ---------------------------------------------------------------------------


def test_fetch_baseline_no_aws_creds_returns_local_fallback(tmp_path, monkeypatch):
    """Dev offline path: boto3 raises NoCredentialsError → read local file.

    Exercises BOTH:
    - The D2 error-handling branch in ``fetch_baseline``.
    - The BLOCK iter1 fix: ``_get_local_dir()`` must re-read the env at call
      time so ``monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", ...)`` lands.
    """
    fallback_dir = tmp_path / "fallback"
    fallback_dir.mkdir(parents=True)
    monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", str(fallback_dir))

    # Seed a local baseline file using the same flat naming the module uses.
    payload = {
        "security": 72.0,
        "quality": 70.0,
        "coverage": 65.0,
        "spec_compliance": 85.0,
        "discipline": 90.0,
        "overall": 78.0,
        "weights_used": {},
        "missing_components": [],
    }
    (fallback_dir / "itsiae-foo-abc.json").write_text(json.dumps(payload))

    from botocore.exceptions import NoCredentialsError

    class _FakeS3:
        def get_object(self, **_kw):
            raise NoCredentialsError()

    def fake_client(*_args, **_kwargs):
        return _FakeS3()

    with patch(
        "lib.review_evidence.baseline_cache.boto3.client",
        side_effect=fake_client,
    ):
        result = fetch_baseline("itsiae/foo", "abc")

    assert result is not None
    assert result.security == 72.0


def test_fetch_baseline_honors_home_monkeypatch(tmp_path, monkeypatch):
    """BLOCK iter1 regression guard: ``monkeypatch.setenv("HOME", ...)`` must
    actually redirect ``_get_local_dir()``.

    Without the on-demand evaluation fix the default ``Path.home()`` would be
    frozen at module import and this assertion would read the developer's
    real home directory.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEVFORGE_BASELINE_LOCAL_DIR", raising=False)

    fallback_dir = tmp_path / ".claude" / "review-evidence-baseline-local"
    fallback_dir.mkdir(parents=True)
    payload = {
        "security": 55.0,
        "quality": 60.0,
        "coverage": 65.0,
        "spec_compliance": 70.0,
        "discipline": 75.0,
        "overall": 65.0,
        "weights_used": {},
        "missing_components": [],
    }
    (fallback_dir / "itsiae-bar-deadbeef.json").write_text(json.dumps(payload))

    from botocore.exceptions import NoCredentialsError

    class _FakeS3:
        def get_object(self, **_kw):
            raise NoCredentialsError()

    with patch(
        "lib.review_evidence.baseline_cache.boto3.client",
        side_effect=lambda *_a, **_kw: _FakeS3(),
    ):
        result = fetch_baseline("itsiae/bar", "deadbeef")

    assert result is not None
    assert result.security == 55.0


# ---------------------------------------------------------------------------
# 5. A2 force-push detection
# ---------------------------------------------------------------------------


def test_sha_exists_in_repo_detects_force_push(tmp_path):
    """Real SHA returns ``True``; a synthetic SHA (force-push proxy) returns ``False``.

    A 40-char hex SHA that doesn't exist locally is the exact signal we get
    after a ``main`` force-push: the cached SHA is unreachable, so the
    baseline must be recomputed.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "x@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=tmp_path,
        check=True,
        env={"GIT_COMMITTER_NAME": "x", "GIT_COMMITTER_EMAIL": "x@example.com", **__import__("os").environ},
    )

    real_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path
    ).decode().strip()
    fake_sha = "0" * 40

    assert sha_exists_in_repo(tmp_path, real_sha) is True
    assert sha_exists_in_repo(tmp_path, fake_sha) is False


def test_baseline_cache_facade_force_push_returns_none(tmp_path, monkeypatch):
    """A2 end-to-end through the ``BaselineCache`` facade.

    A SHA that doesn't exist in the local repo must short-circuit to ``None``
    even if S3 still holds the object, so the caller recomputes.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", str(tmp_path / "fallback"))

    cache = BaselineCache("itsiae/foo", tmp_path)

    # No commit exists, so any SHA is unreachable → force-push semantics.
    assert cache.get("0" * 40) is None
