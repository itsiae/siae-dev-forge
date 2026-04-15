# Task 03 — collect_github.py + test + fixtures

**Goal:** Implementare fetch dati GitHub via `gh graphql` con cache locale + rate limit handling. Produrre fixtures mock per test downstream.

**AC coperti:** AC04a-unit, AC04a-manual, AC15

**Dipendenze:** Task 1

**Tempo stimato:** 30 min

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/collect_github.py` (nuovo)
- `skills/siae-dev-analytics/tests/test_collect_github.py` (nuovo)
- `skills/siae-dev-analytics/tests/fixtures/github_api_response.json` (nuovo)
- `skills/siae-dev-analytics/tests/fixtures/commits_sample.json` (nuovo)

## Step 1 — Crea fixture JSON deterministica

Crea `tests/fixtures/github_api_response.json`:

```json
{
  "repository": {
    "nameWithOwner": "itsiae/sample-repo",
    "pullRequests": {
      "nodes": [
        {
          "number": 101,
          "author": {"login": "alice"},
          "createdAt": "2026-03-01T10:00:00Z",
          "mergedAt": "2026-03-01T14:00:00Z",
          "commits": {"nodes": [{"commit": {"committedDate": "2026-03-01T09:00:00Z"}}]},
          "reviews": {"nodes": [{"createdAt": "2026-03-01T11:00:00Z", "comments": {"totalCount": 2}}]},
          "files": {"nodes": [{"path": "src/auth.py"}, {"path": "tests/test_auth.py"}]},
          "body": "Fixes bug, see docs/plans/2026-02-28-auth-design.md"
        },
        {
          "number": 102,
          "author": {"login": "alice"},
          "createdAt": "2026-03-05T09:00:00Z",
          "mergedAt": "2026-03-07T17:00:00Z",
          "commits": {"nodes": [{"commit": {"committedDate": "2026-03-04T15:00:00Z"}}]},
          "reviews": {"nodes": [{"createdAt": "2026-03-06T10:00:00Z", "comments": {"totalCount": 5}}]},
          "files": {"nodes": [{"path": "src/billing.py"}]},
          "body": "Refactor billing"
        },
        {
          "number": 103,
          "author": {"login": "bob"},
          "createdAt": "2026-03-10T12:00:00Z",
          "mergedAt": "2026-03-10T16:00:00Z",
          "commits": {"nodes": [{"commit": {"committedDate": "2026-03-10T11:00:00Z"}}]},
          "reviews": {"nodes": [{"createdAt": "2026-03-10T13:00:00Z", "comments": {"totalCount": 0}}]},
          "files": {"nodes": [{"path": "src/ui.py"}, {"path": "tests/test_ui.py"}]},
          "body": "Add UI feature per docs/plans/2026-03-01-ui-design.md"
        },
        {
          "number": 104,
          "author": {"login": "bob"},
          "createdAt": "2026-03-15T08:00:00Z",
          "mergedAt": "2026-03-15T18:00:00Z",
          "commits": {"nodes": [{"commit": {"committedDate": "2026-03-14T20:00:00Z"}}]},
          "reviews": {"nodes": [{"createdAt": "2026-03-15T10:00:00Z", "comments": {"totalCount": 3}}]},
          "files": {"nodes": [{"path": "src/api.py"}]},
          "body": "Quick fix"
        },
        {
          "number": 105,
          "author": {"login": "carol"},
          "createdAt": "2026-03-20T14:00:00Z",
          "mergedAt": "2026-03-21T10:00:00Z",
          "commits": {"nodes": [{"commit": {"committedDate": "2026-03-20T13:00:00Z"}}]},
          "reviews": {"nodes": [{"createdAt": "2026-03-20T16:00:00Z", "comments": {"totalCount": 1}}]},
          "files": {"nodes": [{"path": "src/report.py"}, {"path": "tests/test_report.py"}]},
          "body": "New report"
        }
      ]
    },
    "defaultBranchRef": {
      "target": {
        "history": {
          "nodes": [
            {"oid": "abc1", "author": {"user": {"login": "alice"}}, "committedDate": "2026-03-01T09:00:00Z", "message": "feat: auth\n\nverified-by: siae-verification"},
            {"oid": "abc2", "author": {"user": {"login": "alice"}}, "committedDate": "2026-03-04T15:00:00Z", "message": "refactor: billing"},
            {"oid": "abc3", "author": {"user": {"login": "bob"}}, "committedDate": "2026-03-10T11:00:00Z", "message": "feat: ui\n\nverified-by: siae-verification"},
            {"oid": "abc4", "author": {"user": {"login": "bob"}}, "committedDate": "2026-03-14T20:00:00Z", "message": "Revert \"some previous change\""},
            {"oid": "abc5", "author": {"user": {"login": "carol"}}, "committedDate": "2026-03-20T13:00:00Z", "message": "feat: report"}
          ]
        }
      }
    },
    "refs": {
      "nodes": [
        {"name": "COLLAUDO-v1.0.0", "target": {"oid": "abc3"}},
        {"name": "PRODUZIONE-v1.0.0", "target": {"oid": "abc1"}}
      ]
    }
  }
}
```

Crea `tests/fixtures/commits_sample.json` come derivato (50 commit sintetici, cross-dev). Contenuto esatto:

```json
{
  "commits": [
    {"oid": "sha0001", "author": "alice", "date": "2026-03-01T09:00:00Z", "message": "feat: x", "files_changed": 3},
    {"oid": "sha0002", "author": "alice", "date": "2026-03-01T14:00:00Z", "message": "fix: y\n\nverified-by: siae-verification", "files_changed": 1},
    {"oid": "sha0003", "author": "bob", "date": "2026-03-02T10:00:00Z", "message": "feat: z", "files_changed": 5},
    {"oid": "sha0004", "author": "carol", "date": "2026-03-03T08:00:00Z", "message": "refactor: w", "files_changed": 2},
    {"oid": "sha0005", "author": "alice", "date": "2026-03-04T11:00:00Z", "message": "Revert \"commit abc\"", "files_changed": 1}
  ]
}
```

Nota: 5 sample sono sufficienti per test KPI — dimensione reale è irrilevante se copre gli scenari.

## Step 2 — TDD: Scrivi test PRIMA

Crea `tests/test_collect_github.py`:

```python
"""Test per collect_github.py."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

import collect_github as cg


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Cache in directory temporanea."""
    cache_dir = tmp_path / ".cache" / "github"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(cg, "CACHE_DIR", cache_dir)
    return cache_dir


def test_cache_key_deterministic():
    """Stesso repo + window → stesso hash."""
    k1 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    k2 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    assert k1 == k2


def test_cache_key_different_for_different_window():
    """Finestra diversa → hash diverso."""
    k1 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    k2 = cg.cache_key("itsiae/foo", "2026-02-01", "2026-04-01")
    assert k1 != k2


def test_cache_miss_invokes_subprocess(tmp_cache, sample_pr_data):
    """Cold cache → subprocess gh invocato."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(sample_pr_data),
        )
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert mock_run.called
    assert "pullRequests" in data["repository"]


def test_cache_hit_does_not_invoke_subprocess(tmp_cache, sample_pr_data):
    """Warm cache → subprocess NON invocato."""
    # Popola cache
    key = cg.cache_key("itsiae/sample", "2026-03-01", "2026-03-31")
    (tmp_cache / f"{key}.json").write_text(json.dumps(sample_pr_data))

    with patch("subprocess.run") as mock_run:
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert not mock_run.called
    assert data["repository"]["nameWithOwner"] == "itsiae/sample-repo"


def test_rate_limit_triggers_backoff(tmp_cache):
    """Response 'rate limit exceeded' → retry con backoff."""
    responses = [
        MagicMock(returncode=1, stdout="", stderr="API rate limit exceeded"),
        MagicMock(returncode=0, stdout='{"repository": {"pullRequests": {"nodes": []}}}'),
    ]
    with patch("subprocess.run", side_effect=responses), \
         patch("time.sleep") as mock_sleep:
        data = cg.fetch_repo_data("itsiae/foo", "2026-01-01", "2026-02-01")

    assert mock_sleep.called
    assert data["repository"]["pullRequests"] == {"nodes": []}


def test_unauthenticated_raises(tmp_cache):
    """Response 'not authenticated' → RuntimeError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=4, stdout="", stderr="gh: Not authenticated")
        with pytest.raises(RuntimeError, match="authent"):
            cg.fetch_repo_data("itsiae/foo", "2026-01-01", "2026-02-01")


def test_private_repo_no_access_skips(tmp_cache, caplog):
    """Response 'Could not resolve repo' → skip con warning."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Could not resolve to a Repository")
        data = cg.fetch_repo_data("itsiae/private", "2026-01-01", "2026-02-01", skip_on_error=True)
    assert data is None


def test_extract_pr_fields():
    """fetch_repo_data → normalized PR records (dev, repo, cycle_time, ecc.)."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/repo",
            "pullRequests": {"nodes": [
                {
                    "number": 1,
                    "author": {"login": "alice"},
                    "createdAt": "2026-03-01T10:00:00Z",
                    "mergedAt": "2026-03-01T14:00:00Z",
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-03-01T09:00:00Z"}}]},
                    "reviews": {"nodes": []},
                    "files": {"nodes": [{"path": "src/a.py"}]},
                    "body": "",
                }
            ]},
        }
    }
    prs = cg.extract_pr_records(raw)
    assert len(prs) == 1
    assert prs[0]["author"] == "alice"
    assert prs[0]["cycle_time_hours"] == 4.0
    assert prs[0]["repo"] == "itsiae/repo"
    assert prs[0]["number"] == 1


def test_extract_commit_records_with_trailer():
    """Commit con verified-by trailer → flag True."""
    raw = {
        "repository": {
            "defaultBranchRef": {"target": {"history": {"nodes": [
                {"oid": "abc1", "author": {"user": {"login": "alice"}}, "committedDate": "2026-03-01T09:00:00Z",
                 "message": "feat: x\n\nverified-by: siae-verification"},
                {"oid": "abc2", "author": {"user": {"login": "bob"}}, "committedDate": "2026-03-02T10:00:00Z",
                 "message": "fix: y"},
            ]}}}
        }
    }
    commits = cg.extract_commit_records(raw)
    assert len(commits) == 2
    assert commits[0]["has_verified_trailer"] is True
    assert commits[1]["has_verified_trailer"] is False


def test_extract_deploy_tags_attributes_to_commit_author(sample_pr_data):
    """Tag SIAE → attribuiti all'autore del commit taggato."""
    pr_records = cg.extract_pr_records(sample_pr_data)
    commit_records = cg.extract_commit_records(sample_pr_data)
    tag_records = cg.extract_deploy_tags(sample_pr_data, commit_records, pr_records)

    # fixture ha COLLAUDO-v1.0.0 su abc3 (bob) e PRODUZIONE-v1.0.0 su abc1 (alice)
    assert len(tag_records) == 2
    names = {t["tag_name"]: t["attributed_to"] for t in tag_records}
    assert names["COLLAUDO-v1.0.0"] == "bob"
    assert names["PRODUZIONE-v1.0.0"] == "alice"


def test_extract_deploy_tags_filters_non_siae_tags():
    """Tag non-SIAE ignorati (es. 'v1.0.0' da lib)."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/r",
            "defaultBranchRef": {"target": {"history": {"nodes": []}}},
            "refs": {"nodes": [
                {"name": "v1.0.0", "target": {"oid": "abc"}},
                {"name": "release-1.2", "target": {"oid": "def"}},
                {"name": "COLLAUDO-v1", "target": {"oid": "ghi"}},
            ]},
        }
    }
    tags = cg.extract_deploy_tags(raw, [], [])
    assert len(tags) == 1
    assert tags[0]["tag_name"] == "COLLAUDO-v1"
```

## Step 3 — Run test, verifica che falliscono

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pytest tests/test_collect_github.py -v 2>&1 | tail -15
```

Output atteso: `ModuleNotFoundError: No module named 'collect_github'`.

## Step 4 — Implementa `collect_github.py`

Crea `skills/siae-dev-analytics/scripts/collect_github.py`:

```python
"""Collect GitHub data via `gh graphql` with cache and rate limit handling."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/github")


def _ensure_cache_dir() -> Path:
    """Lazy create cache dir. Avoid side effects at module import time."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR

GRAPHQL_QUERY = """
query($owner: String!, $name: String!, $since: DateTime!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    pullRequests(states: MERGED, first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number
        author { login }
        createdAt
        mergedAt
        commits(first: 1) { nodes { commit { committedDate } } }
        reviews(first: 50) { nodes { createdAt comments { totalCount } } }
        files(first: 100) { nodes { path } }
        body
      }
    }
    defaultBranchRef {
      target {
        ... on Commit {
          history(since: $since, first: 100) {
            nodes {
              oid
              author { user { login } }
              committedDate
              message
            }
          }
        }
      }
    }
    refs(refPrefix: "refs/tags/", first: 50) {
      nodes {
        name
        target { oid }
      }
    }
  }
}
"""

VERIFIED_TRAILER = re.compile(r"^verified-by:\s*siae-verification\b", re.MULTILINE | re.IGNORECASE)
DESIGN_LINK = re.compile(r"docs/plans/\S+design\.md", re.IGNORECASE)
REVERT_PATTERN = re.compile(r"^Revert\b", re.IGNORECASE | re.MULTILINE)

# SIAE_TAG_REGEX è centralizzata in compute_kpis.py (AC17).
# Importata via try/except per tollerare import circolari durante il module load.
try:
    from compute_kpis import SIAE_TAG_REGEX  # noqa: E402
except ImportError:
    SIAE_TAG_REGEX = re.compile(r"^(COLLAUDO|CERTIFICAZIONE|PRODUZIONE)[-_/].+$", re.IGNORECASE)


def cache_key(repo: str, since: str, until: str) -> str:
    """Deterministic cache key."""
    h = hashlib.sha256(f"{repo}|{since}|{until}".encode()).hexdigest()[:16]
    return h


def fetch_repo_data(
    repo: str,
    since: str,
    until: str,
    *,
    skip_on_error: bool = False,
    max_retries: int = 3,
) -> Optional[dict]:
    """Fetch PR/commit/tag data for repo in window.

    Returns parsed JSON or None (if skip_on_error=True and repo inaccessible).
    Raises RuntimeError on auth failure or unrecoverable errors.
    """
    key = cache_key(repo, since, until)
    cache_dir = _ensure_cache_dir()
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        log.debug("cache hit: %s", repo)
        return json.loads(cache_file.read_text())

    owner, name = repo.split("/", 1)
    variables = {"owner": owner, "name": name, "since": f"{since}T00:00:00Z"}

    for attempt in range(max_retries):
        result = subprocess.run(
            [
                "gh", "graphql",
                "-f", f"query={GRAPHQL_QUERY}",
                "-F", f"owner={owner}",
                "-F", f"name={name}",
                "-F", f"since={variables['since']}",
            ],
            capture_output=True, text=True, timeout=120,
        )
        stderr = result.stderr or ""
        stdout = result.stdout or ""

        if result.returncode == 0:
            data = json.loads(stdout)
            if "data" in data:
                data = data["data"]
            cache_file.write_text(json.dumps(data, indent=2))
            return data

        if "rate limit" in stderr.lower():
            sleep_s = 60 * (2 ** attempt)
            log.warning("rate limit hit, sleep %ds", sleep_s)
            time.sleep(sleep_s)
            continue

        if "authent" in stderr.lower():
            raise RuntimeError("gh not authenticated. Run `gh auth login`.")

        if "could not resolve" in stderr.lower() or "not found" in stderr.lower():
            log.warning("repo %s inaccessible: %s", repo, stderr.strip())
            if skip_on_error:
                return None
            raise RuntimeError(f"Repo {repo} inaccessible: {stderr}")

        log.error("gh graphql error (attempt %d): %s", attempt + 1, stderr)

    raise RuntimeError(f"gh graphql failed after {max_retries} attempts for {repo}")


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def extract_pr_records(raw: dict) -> list[dict]:
    """Normalizza PR nodes in dict flat per pandas."""
    repo_name = raw.get("repository", {}).get("nameWithOwner", "")
    prs = raw.get("repository", {}).get("pullRequests", {}).get("nodes", [])
    records = []
    for pr in prs:
        author = (pr.get("author") or {}).get("login") or "unknown"
        created = _parse_iso(pr["createdAt"])
        merged = _parse_iso(pr["mergedAt"]) if pr.get("mergedAt") else None
        first_commit = None
        commit_nodes = (pr.get("commits") or {}).get("nodes", [])
        if commit_nodes:
            first_commit = _parse_iso(commit_nodes[0]["commit"]["committedDate"])

        reviews = (pr.get("reviews") or {}).get("nodes", [])
        first_review = min((_parse_iso(r["createdAt"]) for r in reviews), default=None)
        review_comments = sum(r.get("comments", {}).get("totalCount", 0) for r in reviews)

        files = [f["path"] for f in (pr.get("files") or {}).get("nodes", [])]
        has_tests = any(
            "test" in p.lower() or p.endswith(("_test.py", ".test.ts", "Test.java"))
            for p in files
        )

        body = pr.get("body") or ""
        has_design_link = bool(DESIGN_LINK.search(body))

        cycle_time = (merged - created).total_seconds() / 3600 if merged else None
        lead_time = (merged - first_commit).total_seconds() / 3600 if (merged and first_commit) else None
        ttfr = (first_review - created).total_seconds() / 3600 if first_review else None

        records.append({
            "repo": repo_name,
            "number": pr["number"],
            "author": author,
            "created_at": created.isoformat(),
            "merged_at": merged.isoformat() if merged else None,
            "cycle_time_hours": cycle_time,
            "lead_time_hours": lead_time,
            "time_to_first_review_hours": ttfr,
            "review_comments": review_comments,
            "has_tests": has_tests,
            "has_design_link": has_design_link,
        })
    return records


def extract_commit_records(raw: dict) -> list[dict]:
    """Normalizza commit nodes."""
    repo_name = raw.get("repository", {}).get("nameWithOwner", "")
    history = (
        raw.get("repository", {})
        .get("defaultBranchRef", {})
        .get("target", {})
        .get("history", {})
        .get("nodes", [])
    )
    records = []
    for c in history:
        author = ((c.get("author") or {}).get("user") or {}).get("login") or "unknown"
        msg = c.get("message", "")
        records.append({
            "repo": repo_name,
            "oid": c["oid"],
            "author": author,
            "committed_at": c["committedDate"],
            "message": msg,
            "has_verified_trailer": bool(VERIFIED_TRAILER.search(msg)),
            "is_revert": bool(REVERT_PATTERN.search(msg.split("\n")[0])),
        })
    return records


def extract_deploy_tags(raw: dict, commit_records: list[dict], pr_records: list[dict]) -> list[dict]:
    """Estrai tag SIAE e attribuisci a dev via PR merge author (o fallback)."""
    repo_name = raw.get("repository", {}).get("nameWithOwner", "")
    tags = (raw.get("repository", {}).get("refs", {}) or {}).get("nodes", [])

    commit_to_author = {c["oid"]: c["author"] for c in commit_records}
    tag_records = []
    for t in tags:
        name = t.get("name", "")
        if not SIAE_TAG_REGEX.match(name):
            continue
        tag_oid = (t.get("target") or {}).get("oid")
        attributed_dev = commit_to_author.get(tag_oid, "team")
        tag_records.append({
            "repo": repo_name,
            "tag_name": name,
            "commit_oid": tag_oid,
            "attributed_to": attributed_dev,
        })
    return tag_records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--since", required=True, help="ISO date")
    parser.add_argument("--until", default="today")
    args = parser.parse_args()

    data = fetch_repo_data(args.repo, args.since, args.until)
    print(json.dumps({
        "prs": len(extract_pr_records(data)),
        "commits": len(extract_commit_records(data)),
        "tags": len(extract_deploy_tags(data, extract_commit_records(data), extract_pr_records(data))),
    }, indent=2))
```

## Step 5 — Run test, verifica che passano

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pytest tests/test_collect_github.py -v 2>&1 | tail -20
```

Output atteso: `11 passed`.

## Step 6 — Commit

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/collect_github.py \
        skills/siae-dev-analytics/tests/test_collect_github.py \
        skills/siae-dev-analytics/tests/fixtures/github_api_response.json \
        skills/siae-dev-analytics/tests/fixtures/commits_sample.json
git commit -m "feat(skill): add collect_github for siae-dev-analytics [Task 3/7]

- gh graphql query con PR/commit/tag/review
- Cache locale .cache/github/<hash>.json deterministica
- Rate limit handling con exponential backoff (max 3 retry)
- Normalizzazione PR/commit/tag records per pandas
- 11 test pytest pass, mock subprocess
- Fixture github_api_response.json + commits_sample.json

AC04a-unit, AC04a-manual, AC15"
```

## Criteri di accettazione Task 3

- [ ] `collect_github.py` implementa `fetch_repo_data`, `extract_pr_records`, `extract_commit_records`, `extract_deploy_tags`
- [ ] Cache key deterministica (stesso input → stesso hash)
- [ ] Cache miss invoca subprocess, cache hit legge da file
- [ ] Rate limit → exponential backoff (60s, 120s, 240s)
- [ ] Auth error → RuntimeError
- [ ] Repo inaccessibile + skip_on_error=True → None (non crash)
- [ ] 11 test pytest pass
- [ ] Fixture JSON create (github_api_response, commits_sample)
- [ ] Commit conventional

## Verifica

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_collect_github.py -v --tb=short
```

Output atteso: `11 passed`.
