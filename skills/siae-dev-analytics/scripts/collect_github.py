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
query($owner: String!, $name: String!, $since: GitTimestamp!) {
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

# SIAE_TAG_REGEX e' centralizzata in compute_kpis.py (AC17).
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
                "gh", "api", "graphql",
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
