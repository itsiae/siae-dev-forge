"""Entry point CLI per siae-dev-analytics.

Subcommand:
    autodetect → rileva fonti e stampa JSON
    run        → pipeline completa (fetch + compute + export)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import yaml
import pandas as pd

import autodetect_sources as ad
import collect_github as cg
import collect_s3_telemetry as ct
import compute_kpis as ck
import export_excel as ee

log = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    """Load + minimal validate YAML config."""
    data = yaml.safe_load(path.read_text())
    required = ["scope", "time_window"]
    for k in required:
        if k not in data:
            raise ValueError(f"config missing required key: {k}")
    if not (data["scope"].get("repos") or data["scope"].get("teams") or data["scope"].get("topics")):
        raise ValueError("scope must define at least one of: repos, teams, topics")
    return data


def resolve_repos(scope: dict) -> list[str]:
    """Risolve scope → lista repo effective (repos + teams + topics)."""
    repos = list(scope.get("repos", []))
    # teams/topics richiedono gh CLI — best effort
    for team in scope.get("teams", []):
        # es. "itsiae/team-backend" → gh api orgs/itsiae/teams/team-backend/repos
        try:
            import subprocess
            org, slug = team.split("/", 1)
            result = subprocess.run(
                ["gh", "api", f"orgs/{org}/teams/{slug}/repos", "--jq", ".[].full_name"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                repos.extend(result.stdout.strip().split("\n"))
        except Exception as e:
            log.warning("failed to resolve team %s: %s", team, e)

    for topic in scope.get("topics", []):
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "search", "repos", "--topic", topic, "--json", "nameWithOwner",
                 "--jq", ".[].nameWithOwner"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                repos.extend(result.stdout.strip().split("\n"))
        except Exception as e:
            log.warning("failed to resolve topic %s: %s", topic, e)

    return list(set(r for r in repos if r and "/" in r))


def cmd_autodetect(config_path: Path) -> dict:
    report = ad.autodetect(abort_on_no_github=False)
    return report.as_dict()


def cmd_run(config_path: Path, output_override: Path | None = None,
            format_override: str | None = None, anonymize_override: bool | None = None,
            generated_at_override: str | None = None) -> Path:
    cfg = load_config(config_path)

    # Autodetect
    source_report = ad.autodetect(abort_on_no_github=True)
    log.info("mode: %s", source_report.mode())

    # Scope
    repos = resolve_repos(cfg["scope"])
    if not repos:
        raise RuntimeError("no repos resolved from scope")
    log.info("analyzing %d repos", len(repos))

    window = cfg["time_window"]
    since = window["from"]
    until = window.get("to", "today")
    if until == "today":
        until = datetime.today().date().isoformat()

    excluded = set(cfg.get("developers", {}).get("exclude", []))
    include_filter = cfg.get("developers", {}).get("include", [])
    min_commits = cfg.get("options", {}).get("min_commits_threshold", 5)

    # Collect GitHub
    all_prs, all_commits, all_tags = [], [], []
    for repo in repos:
        try:
            raw = cg.fetch_repo_data(repo, since, until, skip_on_error=True)
            if raw is None:
                continue
            prs_records = cg.extract_pr_records(raw)
            commits_records = cg.extract_commit_records(raw)
            tags_records = cg.extract_deploy_tags(raw, commits_records, prs_records)
            all_prs.extend(prs_records)
            all_commits.extend(commits_records)
            all_tags.extend(tags_records)
        except RuntimeError as e:
            log.warning("skipping repo %s: %s", repo, e)

    prs_df = pd.DataFrame(all_prs) if all_prs else pd.DataFrame(
        columns=["repo", "number", "author", "created_at", "merged_at",
                 "cycle_time_hours", "lead_time_hours", "time_to_first_review_hours",
                 "review_comments", "has_tests", "has_design_link"])
    commits_df = pd.DataFrame(all_commits) if all_commits else pd.DataFrame(
        columns=["repo", "oid", "author", "committed_at", "message",
                 "has_verified_trailer", "is_revert"])
    tags_df = pd.DataFrame(all_tags) if all_tags else pd.DataFrame(
        columns=["repo", "tag_name", "commit_oid", "attributed_to"])

    # Filter excluded/included devs
    if not prs_df.empty:
        prs_df = prs_df[~prs_df["author"].isin(excluded)]
        if include_filter:
            prs_df = prs_df[prs_df["author"].isin(include_filter)]
    if not commits_df.empty:
        commits_df = commits_df[~commits_df["author"].isin(excluded)]
        if include_filter:
            commits_df = commits_df[commits_df["author"].isin(include_filter)]
        commits_df = ck.filter_by_min_commits(commits_df, threshold=min_commits)

    # Collect S3 telemetry if available
    cost_scores = {}
    if source_report.s3_devforge:
        events = ct.fetch_devforge_logs(since, until)
        if events:
            # Override Q4 con telemetry (piu' accurate)
            verif = ct.verification_rate_from_events(events)
            if verif and not commits_df.empty:
                # Annota — non fondamentale per la MVP
                log.info("S3 verification_rate override for %d devs", len(verif))

    if source_report.s3_blend:
        costs = ct.fetch_blend_usage(since, until)
        cost_scores = ct.normalize_cost_score(costs)

    # Compute KPIs
    window_tuple = (since, until)
    if prs_df.empty and commits_df.empty:
        log.warning("no data to compute")
        kpis_df = pd.DataFrame()
    else:
        kpis_df = ck.compute_all(prs_df, commits_df, tags_df, window_tuple, cost_scores=cost_scores)

    # Export
    output_cfg = cfg.get("output", {})
    fmt = format_override or output_cfg.get("format", "xlsx")
    out_path = Path(output_override or output_cfg.get("path", "./devforge-analytics-report.xlsx"))
    anonymize = anonymize_override if anonymize_override is not None else cfg.get("options", {}).get("anonymize", False)

    if kpis_df.empty:
        out_path = out_path.with_suffix(".no-data.txt")
        out_path.write_text("No data available for the specified scope + window.\n")
        return out_path

    if fmt in ("xlsx", "both"):
        ee.export(
            kpis_df=kpis_df,
            raw_prs=prs_df,
            source_report=source_report.as_dict(),
            window=window_tuple,
            output_path=out_path,
            anonymize=anonymize,
            generated_at=generated_at_override,  # None → utcnow default
        )
    if fmt in ("csv", "both"):
        csv_path = out_path.with_suffix(".csv")
        kpis_df.to_csv(csv_path)

    return out_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(prog="run_analytics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_auto = sub.add_parser("autodetect")
    p_auto.add_argument("--config", default="devforge-analytics.yml")

    p_run = sub.add_parser("run")
    p_run.add_argument("--config", default="devforge-analytics.yml")
    p_run.add_argument("--output")
    p_run.add_argument("--format", choices=["xlsx", "csv", "both"])
    p_run.add_argument("--anonymize", action="store_true")

    args = parser.parse_args()

    if args.cmd == "autodetect":
        result = cmd_autodetect(Path(args.config))
        print(json.dumps(result, indent=2))
    elif args.cmd == "run":
        out = cmd_run(
            Path(args.config),
            output_override=Path(args.output) if args.output else None,
            format_override=args.format,
            anonymize_override=args.anonymize if args.anonymize else None,
        )
        print(f"Report saved to: {out}")


if __name__ == "__main__":
    main()
