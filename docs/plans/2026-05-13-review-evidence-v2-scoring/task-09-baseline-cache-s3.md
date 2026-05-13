# Task 09 — baseline_cache.py S3 backend + local fallback

**SP:** 3.0 · **AC mappati:** CRITICAL D3+D5, A1, A2 · **Dipendenze:** Task 01 + Task 16 (Terraform) · **Wave:** 3

## Goal

Implementare `lib/review_evidence/baseline_cache.py` con:
- Read S3 GetObject su `s3://itsiae-review-evidence-baseline-prod/<repo>/<sha>.json`
- Write PutObject (CI workflow context, OIDC IAM)
- **A1 fix:** cache key = main HEAD SHA (no TTL)
- **A2 fix:** detect force-push main via `git cat-file -e <sha>`, fallback recompute
- **D2 fix:** local fallback (no AWS creds → `~/.claude/review-evidence-baseline-local/`)

## File coinvolti

**Creare:**
- `lib/review_evidence/baseline_cache.py`
- `tests/test_review_evidence_baseline_cache.py`

## Step TDD

### Step 1 — Test (con `moto` mock S3)

```python
"""Tests for baseline_cache S3 + local fallback."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from lib.review_evidence.baseline_cache import (
    BaselineCache,
    fetch_baseline,
    store_baseline,
    baseline_key,
)
from lib.review_evidence.schema import ScoreCard


S3_BUCKET = "itsiae-review-evidence-baseline-prod"


def _make_scorecard(security=80):
    return ScoreCard(
        security=security, quality=70, coverage=65,
        spec_compliance=85, discipline=90, overall=78,
        weights_used={"security": 0.30, "quality": 0.20, "coverage": 0.20,
                       "spec_compliance": 0.15, "discipline": 0.15},
        missing_components=[],
    )


def test_baseline_key_format():
    assert baseline_key("itsiae/siae-dev-forge", "abc123") == "itsiae/siae-dev-forge/abc123.json"


@mock_aws
def test_fetch_baseline_cache_miss_returns_none():
    boto3.client("s3", region_name="eu-west-1").create_bucket(
        Bucket=S3_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    result = fetch_baseline("itsiae/foo", "missingsha")
    assert result is None


@mock_aws
def test_store_then_fetch_roundtrip():
    boto3.client("s3", region_name="eu-west-1").create_bucket(
        Bucket=S3_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    sc = _make_scorecard(security=85)
    store_baseline("itsiae/foo", "abc123", sc)
    
    fetched = fetch_baseline("itsiae/foo", "abc123")
    assert fetched is not None
    assert fetched.security == 85.0


def test_fetch_baseline_no_aws_creds_returns_local_fallback(tmp_path, monkeypatch):
    """D2: dev senza AWS → local fallback."""
    monkeypatch.setenv("HOME", str(tmp_path))
    fallback_dir = tmp_path / ".claude" / "review-evidence-baseline-local"
    fallback_dir.mkdir(parents=True)
    sc = _make_scorecard(security=72)
    (fallback_dir / "itsiae-foo-abc.json").write_text(json.dumps({
        "security": 72, "quality": 70, "coverage": 65,
        "spec_compliance": 85, "discipline": 90, "overall": 78,
        "weights_used": {}, "missing_components": [],
    }))
    
    # Mock boto3 to raise NoCredentialsError
    from botocore.exceptions import NoCredentialsError
    def fake_client(*args, **kwargs):
        class FakeS3:
            def get_object(self, **kw):
                raise NoCredentialsError()
        return FakeS3()
    
    with patch("lib.review_evidence.baseline_cache.boto3.client", side_effect=fake_client):
        result = fetch_baseline("itsiae/foo", "abc")
    assert result is not None
    assert result.security == 72.0


def test_baseline_a2_force_push_invalidation(tmp_path):
    """A2: force-push main → vecchio SHA non esiste → re-compute (None returned)."""
    import subprocess as sp
    sp.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    
    from lib.review_evidence.baseline_cache import sha_exists_in_repo
    real_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    fake_sha = "0" * 40
    assert sha_exists_in_repo(tmp_path, real_sha) is True
    assert sha_exists_in_repo(tmp_path, fake_sha) is False
```

### Step 2 — Implementa

```python
"""Baseline cache: S3 backend + local fallback + force-push invalidation."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from lib.review_evidence.schema import ScoreCard


S3_BUCKET_DEFAULT = "itsiae-review-evidence-baseline-prod"
S3_REGION_DEFAULT = "eu-west-1"


def _get_s3_bucket() -> str:
    """BLOCK iter1 fix: read env on-demand, not at module-import."""
    return os.environ.get("DEVFORGE_BASELINE_S3_BUCKET", S3_BUCKET_DEFAULT)


def _get_s3_region() -> str:
    return os.environ.get("DEVFORGE_BASELINE_S3_REGION", S3_REGION_DEFAULT)


def _get_local_dir() -> Path:
    """BLOCK iter1 fix: on-demand evaluation so monkeypatch.setenv('HOME', ...)
    in tests actually takes effect (was module-level → frozen at import)."""
    return Path(
        os.environ.get(
            "DEVFORGE_BASELINE_LOCAL_DIR",
            str(Path.home() / ".claude" / "review-evidence-baseline-local"),
        )
    )


def baseline_key(repo_full_name: str, main_sha: str) -> str:
    """Key shape: itsiae/repo/<sha>.json."""
    return f"{repo_full_name}/{main_sha}.json"


def _local_key(repo_full_name: str, main_sha: str) -> Path:
    """Local fallback filename."""
    safe = repo_full_name.replace("/", "-")
    return _get_local_dir() / f"{safe}-{main_sha}.json"


def fetch_baseline(repo_full_name: str, main_sha: str) -> Optional[ScoreCard]:
    """Read baseline from S3, falls back to local file if AWS unreachable.

    A1 fix: key = main_sha, no TTL.
    D2 fix: NoCredentialsError → local fallback.
    """
    try:
        client = boto3.client("s3", region_name=_get_s3_region())
        resp = client.get_object(Bucket=_get_s3_bucket(),
                                  Key=baseline_key(repo_full_name, main_sha))
        data = json.loads(resp["Body"].read())
        return ScoreCard(**data)
    except (BotoCoreError, ClientError, NoCredentialsError):
        return _local_fallback_read(repo_full_name, main_sha)
    except Exception:
        return None


def store_baseline(repo_full_name: str, main_sha: str, scores: ScoreCard) -> bool:
    """Write to S3 (CI context with OIDC). Returns success bool."""
    try:
        client = boto3.client("s3", region_name=_get_s3_region())
        client.put_object(
            Bucket=_get_s3_bucket(),
            Key=baseline_key(repo_full_name, main_sha),
            Body=json.dumps(asdict(scores), indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except (BotoCoreError, ClientError, NoCredentialsError):
        # Fall back to local write (dev offline)
        return _local_fallback_write(repo_full_name, main_sha, scores)


def _local_fallback_read(repo: str, sha: str) -> Optional[ScoreCard]:
    p = _local_key(repo, sha)
    if not p.exists():
        return None
    try:
        return ScoreCard(**json.loads(p.read_text()))
    except (json.JSONDecodeError, TypeError):
        return None


def _local_fallback_write(repo: str, sha: str, scores: ScoreCard) -> bool:
    p = _local_key(repo, sha)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(scores), indent=2))
    return True


def sha_exists_in_repo(repo_root: Path, sha: str) -> bool:
    """A2: detect force-push or amended commit. False → re-compute baseline."""
    try:
        p = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=repo_root, capture_output=True, timeout=5, check=False,
        )
        return p.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class BaselineCache:
    """High-level facade for orchestrator."""

    def __init__(self, repo_full_name: str, repo_root: Path):
        self.repo_full_name = repo_full_name
        self.repo_root = repo_root

    def get(self, main_sha: str) -> Optional[ScoreCard]:
        if not sha_exists_in_repo(self.repo_root, main_sha):
            return None  # A2: force-push → recompute
        return fetch_baseline(self.repo_full_name, main_sha)

    def put(self, main_sha: str, scores: ScoreCard) -> bool:
        return store_baseline(self.repo_full_name, main_sha, scores)
```

### Step 3 — Run + commit

```bash
pip install moto boto3  # if not available
python3 -m pytest tests/test_review_evidence_baseline_cache.py -v
# 5 passed

git add lib/review_evidence/baseline_cache.py tests/test_review_evidence_baseline_cache.py
git commit -m "feat(review-evidence-v2): baseline_cache S3 + local fallback + A1+A2+D2 fixes (#task-09)"
```

## Criteri di accettazione

- [ ] **CRITICAL D3+D5:** S3 backed via boto3 (server-side, no client trust)
- [ ] **CRITICAL A1:** key = main HEAD SHA, no TTL check
- [ ] **A2:** `sha_exists_in_repo()` detect force-push → returns None
- [ ] **D2:** NoCredentialsError → local fallback `~/.claude/review-evidence-baseline-local/`
- [ ] Bucket name configurabile via env `DEVFORGE_BASELINE_S3_BUCKET`
- [ ] `boto3` + `moto` (test dep) in `requirements-test.txt`
- [ ] 5 test PASS
- [ ] No regression v1
