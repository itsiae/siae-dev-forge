#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
Branching Strategy Compliance Check — DevForge

Verifica che i repository SIAE rispettino la branching strategy:
- Default branch deve essere main
- Solo release/** puo' aprire PR verso main

Modalita':
  --current         Check solo il repo corrente (default)
  --review          Check PR dove l'utente e' reviewer nell'org
  --topics TOPIC..  Espansione per topic GitHub

Esegui con: python3 check_branching.py [--current] [--review] [--topics t1 t2]
Output: report markdown su stdout, errori su stderr.

Exit codes: 0 = tutto compliant, 1 = violazioni trovate, 2 = errore.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Set


@dataclass
class Violation:
    repo: str
    kind: str  # "default_branch" | "pr_targets_main"
    detail: str
    source: str  # "corrente" | "review" | "topic: {name}"
    pr_number: Optional[int] = None
    branch: Optional[str] = None


@dataclass
class CompliantPR:
    repo: str
    pr_number: int
    branch: str
    target: str


@dataclass
class ExemptPR:
    repo: str
    pr_number: int
    branch: str
    target: str


@dataclass
class Report:
    violations: List[Violation] = field(default_factory=list)
    compliant: List[CompliantPR] = field(default_factory=list)
    exempt: List[ExemptPR] = field(default_factory=list)
    repos_checked: Set[str] = field(default_factory=set)
    current_repo: str = ""
    review_pr_count: int = 0
    topic_repo_count: int = 0


def run_gh(args: list, timeout: int = 30) -> Optional[str]:
    """Run a gh CLI command, return stdout or None on failure."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            print(f"  gh {' '.join(args[:3])}... failed: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        print("ERROR: gh CLI not found. Install: https://cli.github.com/", file=sys.stderr)
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print(f"  gh {' '.join(args[:3])}... timed out ({timeout}s)", file=sys.stderr)
        return None


def check_default_branch(repo: str) -> Optional[str]:
    """Return default branch name, or None on failure."""
    out = run_gh(["repo", "view", repo, "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"])
    return out if out else None


def check_prs_targeting_main(repo: str) -> list:
    """Return list of open PRs targeting main."""
    out = run_gh(["pr", "list", "--repo", repo, "--base", "main", "--state", "open",
                  "--json", "number,title,headRefName"])
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def check_repo(repo: str, source: str, report: Report) -> None:
    """Run both controls on a single repo."""
    if repo in report.repos_checked:
        return
    report.repos_checked.add(repo)

    print(f"  Checking {repo} ({source})...", file=sys.stderr)

    # Control A: default branch
    default_branch = check_default_branch(repo)
    if default_branch and default_branch != "main":
        report.violations.append(Violation(
            repo=repo, kind="default_branch",
            detail=f"`{default_branch}` (atteso: `main`)",
            source=source
        ))

    # Control B: PRs targeting main from non-release branches
    prs = check_prs_targeting_main(repo)
    for pr in prs:
        head = pr.get("headRefName", "")
        num = pr.get("number", 0)
        if head.startswith("release/"):
            report.compliant.append(CompliantPR(
                repo=repo, pr_number=num, branch=head, target="main"
            ))
        else:
            report.violations.append(Violation(
                repo=repo, kind="pr_targets_main",
                detail=f"PR #{num} from `{head}` targets main",
                source=source, pr_number=num, branch=head
            ))


def check_review_prs(repo: str, pr_number: int, head: str, base: str,
                     source: str, report: Report) -> None:
    """Check a specific PR found via review search."""
    if base == "main":
        if head.startswith("release/"):
            report.compliant.append(CompliantPR(
                repo=repo, pr_number=pr_number, branch=head, target="main"
            ))
        else:
            report.violations.append(Violation(
                repo=repo, kind="pr_targets_main",
                detail=f"PR #{pr_number} from `{head}` targets main",
                source=source, pr_number=pr_number, branch=head
            ))
    else:
        report.exempt.append(ExemptPR(
            repo=repo, pr_number=pr_number, branch=head, target=base
        ))


def phase_current(report: Report) -> None:
    """Phase 1: check current repo."""
    out = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if not out:
        print("  Not in a GitHub repo, skipping current repo check.", file=sys.stderr)
        return
    report.current_repo = out
    check_repo(out, "corrente", report)


def phase_review(report: Report) -> None:
    """Phase 2: check PRs where user is reviewer in itsiae org."""
    out = run_gh(["search", "prs", "--review-requested=@me", "--state=open",
                  "--owner=itsiae", "--json", "repository,number,title,url"])
    if not out:
        print("  No PRs in review found.", file=sys.stderr)
        return

    try:
        prs = json.loads(out)
    except json.JSONDecodeError:
        print("  Failed to parse review PR list.", file=sys.stderr)
        return

    report.review_pr_count = len(prs)

    repos_from_review: set = set()
    for pr in prs:
        repo_info = pr.get("repository", {})
        repo_name = repo_info.get("nameWithOwner", "")
        if not repo_name:
            continue
        repos_from_review.add(repo_name)

        detail_out = run_gh(["pr", "view", str(pr["number"]), "--repo", repo_name,
                             "--json", "headRefName,baseRefName",
                             "-q", r'"\(.headRefName)\t\(.baseRefName)"'])
        if not detail_out:
            continue
        parts = detail_out.strip('"').split("\t")
        if len(parts) != 2:
            continue
        head, base = parts
        check_review_prs(repo_name, pr["number"], head, base, "review", report)

    for repo_name in repos_from_review:
        if repo_name not in report.repos_checked:
            report.repos_checked.add(repo_name)
            default_branch = check_default_branch(repo_name)
            if default_branch and default_branch != "main":
                report.violations.append(Violation(
                    repo=repo_name, kind="default_branch",
                    detail=f"`{default_branch}` (atteso: `main`)",
                    source="review"
                ))


def phase_topics(topics: list, report: Report) -> None:
    """Phase 3: expand by GitHub topics."""
    all_repos: set = set()

    for topic in topics:
        print(f"  Searching repos with topic '{topic}'...", file=sys.stderr)
        out = run_gh(["search", "repos", "--owner=itsiae", f"--topic={topic}",
                      "--json", "fullName", "-q", ".[].fullName"])
        if out:
            for repo in out.split("\n"):
                repo = repo.strip()
                if repo and repo not in report.repos_checked:
                    all_repos.add(repo)

    report.topic_repo_count = len(all_repos)

    for repo in sorted(all_repos):
        check_repo(repo, "topic", report)


def get_topics_from_repos(repos: set) -> list:
    """Get unique topics from a set of repos."""
    topics: set = set()
    for repo in repos:
        out = run_gh(["repo", "view", repo, "--json", "repositoryTopics",
                      "-q", "[.repositoryTopics[].name] | join(\",\")"])
        if out:
            for t in out.split(","):
                t = t.strip()
                if t:
                    topics.add(t)
    return sorted(topics)


def render_report(report: Report) -> str:
    """Render the compliance report as markdown."""
    lines: list = []

    viol_default = [v for v in report.violations if v.kind == "default_branch"]
    viol_pr = [v for v in report.violations if v.kind == "pr_targets_main"]
    total_viols = len(report.violations)

    lines.append("## Branching Strategy Compliance Report")
    lines.append("")
    lines.append(f"Data: {date.today().isoformat()}")
    if report.current_repo:
        lines.append(f"Repo corrente: {report.current_repo}")
    if report.review_pr_count > 0:
        lines.append(f"PR in review: {report.review_pr_count}")
    if report.topic_repo_count > 0:
        lines.append(f"Repository da espansione topic: {report.topic_repo_count}")
    lines.append(f"Repository totali analizzati: {len(report.repos_checked)}")
    lines.append("")
    lines.append("### Sommario")
    lines.append("")
    lines.append(f"- **{total_viols} VIOLAZIONI**")
    lines.append(f"- {len(report.compliant)} PR/repo compliant")
    lines.append(f"- {len(report.exempt)} PR non soggette (target != main)")
    lines.append("")
    lines.append("---")

    if total_viols == 0:
        lines.append("")
        lines.append("✅ Tutti i repository analizzati sono compliant con la branching strategy SIAE.")
        lines.append("")
    else:
        lines.append("")
        lines.append("### VIOLAZIONI")
        lines.append("")

        if viol_default:
            lines.append("#### Default branch non main")
            lines.append("")
            lines.append("| Repository | Default Branch | Fonte |")
            lines.append("|---|---|---|")
            for v in viol_default:
                lines.append(f"| {v.repo} | {v.detail} | {v.source} |")
            lines.append("")

        if viol_pr:
            lines.append("#### PR verso main da branch non-release")
            lines.append("")
            lines.append("| Repository | PR | Branch | Target | Fonte |")
            lines.append("|---|---|---|---|---|")
            for v in viol_pr:
                lines.append(f"| {v.repo} | #{v.pr_number} | `{v.branch}` | main | {v.source} |")
            lines.append("")

        lines.append("---")

    if report.compliant:
        lines.append("")
        lines.append("### PR compliant")
        lines.append("")
        lines.append("| Repository | PR | Branch | Target |")
        lines.append("|---|---|---|---|")
        for c in report.compliant:
            lines.append(f"| {c.repo} | #{c.pr_number} | `{c.branch}` | {c.target} |")
        lines.append("")

    if report.exempt:
        lines.append("")
        lines.append("### PR non soggette")
        lines.append("")
        lines.append("| Repository | PR | Branch | Target |")
        lines.append("|---|---|---|---|")
        for e in report.exempt:
            lines.append(f"| {e.repo} | #{e.pr_number} | `{e.branch}` | {e.target} |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Branching Strategy Compliance Check — DevForge"
    )
    parser.add_argument("--current", action="store_true", default=False,
                        help="Check current repo (default if no flag given)")
    parser.add_argument("--review", action="store_true", default=False,
                        help="Check PRs where user is reviewer in itsiae org")
    parser.add_argument("--topics", nargs="*", default=None,
                        help="Expand check to repos with these GitHub topics")
    parser.add_argument("--discover-topics", action="store_true", default=False,
                        help="Discover topics from review repos and list them")
    parser.add_argument("--json-output", action="store_true", default=False,
                        help="Output raw JSON instead of markdown report")
    args = parser.parse_args()

    if not args.current and not args.review and args.topics is None and not args.discover_topics:
        args.current = True

    auth = run_gh(["auth", "status"], timeout=10)
    if auth is None:
        print("ERROR: gh auth not configured. Run: gh auth login", file=sys.stderr)
        sys.exit(2)

    report = Report()

    if args.current:
        print("Phase 1: checking current repo...", file=sys.stderr)
        phase_current(report)

    if args.review:
        print("Phase 2: checking PRs in review...", file=sys.stderr)
        phase_review(report)

    if args.discover_topics:
        repos = report.repos_checked.copy()
        if not repos:
            print("No repos checked yet. Run with --current or --review first.", file=sys.stderr)
            sys.exit(2)
        topics = get_topics_from_repos(repos)
        if topics:
            print("Topics found:", file=sys.stderr)
            for t in topics:
                print(f"  - {t}", file=sys.stderr)
            print("\nRun with --topics " + " ".join(topics) + " to expand.", file=sys.stderr)
        else:
            print("No topics found on checked repos.", file=sys.stderr)
        if not args.json_output:
            print(render_report(report))
        return

    if args.topics is not None:
        topics = args.topics if args.topics else []
        if not topics:
            topics = get_topics_from_repos(report.repos_checked)
        if topics:
            print(f"Phase 3: expanding by topics ({', '.join(topics)})...", file=sys.stderr)
            phase_topics(topics, report)
        else:
            print("No topics to expand.", file=sys.stderr)

    if args.json_output:
        output = {
            "violations": [
                {"repo": v.repo, "kind": v.kind, "detail": v.detail,
                 "source": v.source, "pr_number": v.pr_number, "branch": v.branch}
                for v in report.violations
            ],
            "compliant_count": len(report.compliant),
            "exempt_count": len(report.exempt),
            "repos_checked": sorted(report.repos_checked),
            "has_violations": len(report.violations) > 0,
        }
        print(json.dumps(output, indent=2))
    else:
        print(render_report(report))

    sys.exit(1 if report.violations else 0)


if __name__ == "__main__":
    main()
