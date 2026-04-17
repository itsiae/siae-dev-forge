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
CACHE_TTL_DAYS = 7


def _ensure_cache_dir() -> Path:
    """Lazy create cache dir. Avoid side effects at module import time."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _is_cache_fresh(cache_file: Path) -> bool:
    """True se il file cache è stato modificato meno di CACHE_TTL_DAYS giorni fa."""
    import time
    if not cache_file.exists():
        return False
    age_seconds = time.time() - cache_file.stat().st_mtime
    return age_seconds < (CACHE_TTL_DAYS * 86400)

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
        reviews(first: 50) { nodes { author { login } state createdAt comments { totalCount } } }
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
    if _is_cache_fresh(cache_file):
        log.debug("cache hit (fresh): %s", repo)
        return json.loads(cache_file.read_text())
    if cache_file.exists():
        log.debug("cache expired (>%d days): %s — refetching", CACHE_TTL_DAYS, repo)

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
            # Warn on potential pagination truncation (v1 uses first: 100)
            _warn_if_truncated(data, repo)
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


PAGE_SIZE = 100


def _warn_if_truncated(raw: dict, repo: str) -> None:
    """Log WARNING quando conteggio nodes raggiunge PAGE_SIZE (possibile truncation)."""
    repo_data = raw.get("repository") or {}
    prs = (repo_data.get("pullRequests") or {}).get("nodes") or []
    if len(prs) >= PAGE_SIZE:
        log.warning(
            "repo %s returned %d PRs (page size max) — results may be truncated. "
            "Consider narrowing the time window.", repo, len(prs)
        )
    history = ((repo_data.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}
    commits = history.get("nodes") or []
    if len(commits) >= PAGE_SIZE:
        log.warning(
            "repo %s returned %d commits (page size max) — results may be truncated. "
            "Consider narrowing the time window.", repo, len(commits)
        )


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


# ────────────────────────────────────────────────────────
# Branch tracking (task-04)
# ────────────────────────────────────────────────────────

BRANCHES_GRAPHQL = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/heads/", first: 200, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      nodes {
        name
        target { ... on Commit {
          oid
          committedDate
          author { user { login } }
          history(first: 1) { totalCount }
          associatedPullRequests(first: 3) {
            nodes { number state isDraft }
          }
        }}
      }
    }
  }
}
"""


def fetch_branches(
    repo: str,
    since: str,
    *,
    max_retries: int = 3,
) -> list[dict]:
    """Fetch branch refs for repo via GraphQL.

    Returns list of normalized branch dicts with keys:
    name, author, last_commit_at, commit_count, pr_count, prs.

    Raises RuntimeError on auth failure or unrecoverable errors.
    """
    owner, name = repo.split("/", 1)

    for attempt in range(max_retries):
        result = subprocess.run(
            [
                "gh", "api", "graphql",
                "-f", f"query={BRANCHES_GRAPHQL}",
                "-F", f"owner={owner}",
                "-F", f"name={name}",
            ],
            capture_output=True, text=True, timeout=120,
        )
        stderr = result.stderr or ""
        stdout = result.stdout or ""

        if result.returncode == 0:
            data = json.loads(stdout)
            if "data" in data:
                data = data["data"]
            return _extract_branch_records(data, since)

        if "rate limit" in stderr.lower():
            sleep_s = 60 * (2 ** attempt)
            log.warning("fetch_branches: rate limit hit, sleep %ds", sleep_s)
            time.sleep(sleep_s)
            continue

        if "authent" in stderr.lower():
            raise RuntimeError("gh not authenticated. Run `gh auth login`.")

        if "could not resolve" in stderr.lower() or "not found" in stderr.lower():
            log.warning("fetch_branches: repo %s inaccessible: %s", repo, stderr.strip())
            return []

        log.error("fetch_branches: gh graphql error (attempt %d): %s", attempt + 1, stderr)

    raise RuntimeError(f"fetch_branches failed after {max_retries} attempts for {repo}")


def _extract_branch_records(raw: dict, since: str) -> list[dict]:
    """Normalize refs nodes into flat branch dicts."""
    refs = (raw.get("repository") or {}).get("refs", {}).get("nodes", [])
    since_dt = _parse_iso(f"{since}T00:00:00Z") if since else None
    records = []
    for ref in refs:
        name = ref.get("name", "")
        target = ref.get("target") or {}
        committed_date = target.get("committedDate")
        if not committed_date:
            continue
        if since_dt and _parse_iso(committed_date) < since_dt:
            continue
        author = ((target.get("author") or {}).get("user") or {}).get("login") or "unknown"
        commit_count = (target.get("history") or {}).get("totalCount", 0)
        prs_nodes = (target.get("associatedPullRequests") or {}).get("nodes", [])
        records.append({
            "name": name,
            "author": author,
            "last_commit_at": committed_date,
            "commit_count": commit_count,
            "pr_count": len(prs_nodes),
            "prs": [{"number": p["number"], "state": p["state"], "isDraft": p.get("isDraft", False)}
                    for p in prs_nodes],
        })
    return records


# ────────────────────────────────────────────────────────
# Co-Authored-By trailer extraction (task-05)
# ────────────────────────────────────────────────────────

CO_AUTHORED_RE = re.compile(
    r"^Co-Authored-By:\s*(.+?)\s*<(.+?)>",
    re.MULTILINE | re.IGNORECASE,
)


def extract_co_authored(commit_message: str) -> list:
    """Returns list of co-author emails from Co-Authored-By trailers."""
    if not commit_message:
        return []
    matches = CO_AUTHORED_RE.findall(commit_message)
    return [m[1] for m in matches]  # email


# ────────────────────────────────────────────────────────
# Review records extraction (task-05)
# ────────────────────────────────────────────────────────

def extract_review_records(raw: dict) -> list:
    """Estrai review records from PR GraphQL response.

    Returns list of dicts: {reviewer, pr_number, state, created_at,
    target_author, pr_latest_commit_at}.
    """
    prs = raw.get("repository", {}).get("pullRequests", {}).get("nodes", [])
    records = []
    for pr in prs:
        pr_author = (pr.get("author") or {}).get("login") or "unknown"
        pr_number = pr.get("number")

        # Latest commit date on the PR
        commit_nodes = (pr.get("commits") or {}).get("nodes", [])
        pr_latest_commit_at = None
        if commit_nodes:
            pr_latest_commit_at = commit_nodes[0]["commit"]["committedDate"]

        reviews = (pr.get("reviews") or {}).get("nodes", [])
        for review in reviews:
            reviewer_login = (review.get("author") or {}).get("login") or "unknown"
            records.append({
                "reviewer": reviewer_login,
                "pr_number": pr_number,
                "state": review.get("state", "COMMENTED"),
                "created_at": review.get("createdAt", ""),
                "target_author": pr_author,
                "pr_latest_commit_at": pr_latest_commit_at,
            })
    return records


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
