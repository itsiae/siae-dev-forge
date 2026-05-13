"""Baseline cache: S3 backend + local fallback + force-push invalidation.

Backs the regression-vs-baseline scoring loop:

- S3 read/write of ScoreCard JSON keyed by ``<repo>/<main_sha>.json``
- Local fallback under ``~/.claude/review-evidence-baseline-local/`` when the
  process has no AWS credentials (dev offline path — D2 fix).
- ``sha_exists_in_repo`` to detect force-push / amended ``main`` so a stale
  baseline gets re-computed instead of being silently re-used (A2 fix).

Design contracts (from PR brainstorming):

- **A1 (CRITICAL):** the cache key is the ``main`` HEAD SHA. There is NO TTL —
  a SHA never gets "stale": either it still exists in the repo (cache hit) or
  history was rewritten (force-push) and the baseline must be re-computed.
- **D3 + D5 (CRITICAL):** the canonical store is S3 (server-side, OIDC-gated
  via Terraform — Task 16). The client never trusts a local-only baseline as
  authoritative; the local file is a fallback for the dev loop only.
- **BLOCK iter1:** all env-driven config (bucket, region, local dir) is read
  *on demand* in functions, never frozen at module import. This is the only
  way ``monkeypatch.setenv("HOME", tmp_path)`` in tests can actually move the
  local fallback directory — module-level ``Path.home()`` would have been
  resolved before the fixture runs.
"""
from __future__ import annotations

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
    """Resolve the baseline bucket at call time (BLOCK iter1 fix).

    Reading the env var here — rather than capturing it in a module-level
    constant — lets tests and CI override ``DEVFORGE_BASELINE_S3_BUCKET``
    without re-importing the module.
    """
    return os.environ.get("DEVFORGE_BASELINE_S3_BUCKET", S3_BUCKET_DEFAULT)


def _get_s3_region() -> str:
    """Resolve the AWS region at call time (BLOCK iter1 fix)."""
    return os.environ.get("DEVFORGE_BASELINE_S3_REGION", S3_REGION_DEFAULT)


def _get_local_dir() -> Path:
    """Resolve the local fallback directory at call time (BLOCK iter1 fix).

    Tests rely on ``monkeypatch.setenv("HOME", tmp_path)`` to redirect this
    path into a sandbox — that only works if ``Path.home()`` is evaluated
    *after* the monkeypatch runs, not at module import.
    """
    return Path(
        os.environ.get(
            "DEVFORGE_BASELINE_LOCAL_DIR",
            str(Path.home() / ".claude" / "review-evidence-baseline-local"),
        )
    )


def baseline_key(repo_full_name: str, main_sha: str) -> str:
    """Compose the S3 object key for a (repo, sha) baseline.

    Shape: ``<owner>/<repo>/<sha>.json`` — matches the IAM policy prefix and
    keeps one object per immutable commit (A1: no TTL).
    """
    return f"{repo_full_name}/{main_sha}.json"


def _local_key(repo_full_name: str, main_sha: str) -> Path:
    """Compose the local fallback file path for a (repo, sha) baseline.

    Filename collapses the ``owner/repo`` slash into ``-`` so we keep a flat
    directory (no nested mkdir choreography on the dev box).
    """
    safe = repo_full_name.replace("/", "-")
    return _get_local_dir() / f"{safe}-{main_sha}.json"


def fetch_baseline(repo_full_name: str, main_sha: str) -> Optional[ScoreCard]:
    """Read a baseline ScoreCard from S3, fall back to the local file.

    Returns ``None`` on cache miss (S3 ``NoSuchKey`` and no local file) so the
    caller can decide whether to recompute. AWS-credential failures and other
    transport errors transparently fall through to the local store — that is
    the dev-offline path (D2 fix).

    Note on key semantics (A1 fix): the key embeds the ``main`` HEAD SHA, so
    a hit implies the baseline still corresponds to the current ``main`` tip.
    Force-push detection is handled separately via ``sha_exists_in_repo`` —
    this function does not introspect git.
    """
    try:
        client = boto3.client("s3", region_name=_get_s3_region())
        resp = client.get_object(
            Bucket=_get_s3_bucket(),
            Key=baseline_key(repo_full_name, main_sha),
        )
        data = json.loads(resp["Body"].read())
        return ScoreCard(**_scorecard_kwargs(data))
    except (NoCredentialsError, BotoCoreError, ClientError):
        # D2: dev offline / no AWS creds / NoSuchKey — try the local fallback.
        # ClientError covers the moto-emulated NoSuchKey as well as real
        # transport errors; both end up at the same recovery path.
        return _local_fallback_read(repo_full_name, main_sha)
    except (json.JSONDecodeError, TypeError):
        # Corrupted payload — surface as cache miss, don't crash the caller.
        return None


def store_baseline(repo_full_name: str, main_sha: str, scores: ScoreCard) -> bool:
    """Persist a baseline ScoreCard.

    Normal path: S3 PutObject. The CI workflow assumes an OIDC role that
    grants ``s3:PutObject`` only on the baseline prefix (Task 16 Terraform).
    Dev path: if AWS calls fail we write to the local fallback so the local
    review loop still works — but the canonical store is S3 (D3+D5).
    """
    try:
        client = boto3.client("s3", region_name=_get_s3_region())
        client.put_object(
            Bucket=_get_s3_bucket(),
            Key=baseline_key(repo_full_name, main_sha),
            Body=json.dumps(asdict(scores), indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except (NoCredentialsError, BotoCoreError, ClientError):
        # D2: best-effort local write so the dev review loop has something to
        # diff against on the next run. Not authoritative — CI will overwrite.
        return _local_fallback_write(repo_full_name, main_sha, scores)


def _scorecard_kwargs(data: dict) -> dict:
    """Strip unknown keys so a forward-compat baseline payload still loads.

    Mirrors the ``_safe_kwargs`` discipline used elsewhere in
    ``review_evidence.schema``.
    """
    known = ScoreCard.__dataclass_fields__
    return {k: v for k, v in data.items() if k in known}


def _local_fallback_read(repo: str, sha: str) -> Optional[ScoreCard]:
    """Read a baseline from the local fallback directory.

    Returns ``None`` if the file does not exist or is corrupt — corruption is
    treated as a cache miss rather than a crash, so the caller will simply
    recompute the baseline.
    """
    p = _local_key(repo, sha)
    if not p.exists():
        return None
    try:
        return ScoreCard(**_scorecard_kwargs(json.loads(p.read_text())))
    except (json.JSONDecodeError, TypeError, OSError):
        return None


def _local_fallback_write(repo: str, sha: str, scores: ScoreCard) -> bool:
    """Write a baseline to the local fallback directory.

    Creates the parent dir on demand. The caller treats the bool only as a
    signal for log lines — losing a local write isn't a hard failure.
    """
    p = _local_key(repo, sha)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(scores), indent=2))
        return True
    except OSError:
        return False


def sha_exists_in_repo(repo_root: Path, sha: str) -> bool:
    """Return whether ``sha`` is still reachable in the local git repo.

    Used to detect force-push / amended ``main`` (A2 fix): when the cached
    baseline's SHA no longer exists locally, history has been rewritten and
    the baseline must be recomputed against the new tip.

    Implementation uses ``git cat-file -e <sha>`` because:

    - It's cheap (no object content read, just existence check).
    - It returns exit code 0 iff the object exists in the local object store
      — no false positives from refs that happen to share a prefix.
    - It tolerates short SHAs the same way the rest of git does.

    ``FileNotFoundError`` (no ``git`` in PATH) and ``TimeoutExpired`` (huge
    repo on a slow disk) both return ``False`` so the caller falls back to
    recompute — the only safe answer when we can't tell.
    """
    try:
        p = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=str(repo_root),
            capture_output=True,
            timeout=5,
            check=False,
        )
        return p.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class BaselineCache:
    """High-level facade combining force-push detection + storage.

    The orchestrator uses this rather than the module-level functions so the
    repo identity (``owner/repo`` + working tree path) is bound once and the
    call sites stay clean.
    """

    def __init__(self, repo_full_name: str, repo_root: Path):
        self.repo_full_name = repo_full_name
        self.repo_root = repo_root

    def get(self, main_sha: str) -> Optional[ScoreCard]:
        """Return the cached baseline or ``None`` if it must be recomputed.

        Returns ``None`` in two cases:

        1. **A2:** the cached SHA no longer exists locally (force-push) — the
           baseline is conceptually invalid even if S3 still has the object.
        2. Plain cache miss (S3 + local both empty).
        """
        if not sha_exists_in_repo(self.repo_root, main_sha):
            return None  # A2: force-push → caller must recompute
        return fetch_baseline(self.repo_full_name, main_sha)

    def put(self, main_sha: str, scores: ScoreCard) -> bool:
        """Persist a baseline. See ``store_baseline`` for backend semantics."""
        return store_baseline(self.repo_full_name, main_sha, scores)
