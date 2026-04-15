"""Entry point CLI per siae-dev-analytics.

Subcommand:
    autodetect → rileva fonti e stampa JSON
    run        → pipeline completa (fetch + compute + export)
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import yaml
import pandas as pd
from pydantic import BaseModel, Field, ValidationError

import autodetect_sources as ad
import collect_github as cg
import collect_s3_telemetry as ct
import compute_kpis as ck
import export_excel as ee

log = logging.getLogger(__name__)

# Bot e account di servizio esclusi di default (sempre applicato + merge con config)
DEFAULT_BOT_EXCLUDE = {
    "dependabot[bot]", "renovate[bot]", "github-actions[bot]",
    "github-actions", "copilot[bot]", "pre-commit-ci[bot]",
    "codecov[bot]", "snyk-bot", "unknown",
}


# ────────────────────────────────────────────────────────
# Pydantic models per config validation (AC01 conformance)
# ────────────────────────────────────────────────────────

class ScopeConfig(BaseModel):
    repos: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class TimeWindowConfig(BaseModel):
    from_: str = Field(alias="from")
    to: str = Field(default="today")

    class Config:
        populate_by_name = True


class DevelopersConfig(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class OptionsConfig(BaseModel):
    anonymize: bool = False
    min_commits_threshold: int = 5
    parallel_fetch: int = 4


class OutputConfig(BaseModel):
    format: str = Field(default="xlsx", pattern="^(xlsx|csv|both)$")
    path: str = "./devforge-analytics-report.xlsx"


class AnalyticsConfig(BaseModel):
    version: int = 1
    scope: ScopeConfig
    time_window: TimeWindowConfig
    developers: DevelopersConfig = Field(default_factory=DevelopersConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(path: Path) -> dict:
    """Load + validate YAML config via Pydantic (AC01).

    Raises ValueError con errori dettagliati riga+campo se validazione fallisce.
    """
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML in {path}: {e}")
    if raw is None:
        raise ValueError(f"config {path} is empty")

    try:
        cfg = AnalyticsConfig(**raw)
    except ValidationError as e:
        raise ValueError(f"config validation failed:\n{e}")

    # Constraint business: scope deve definire almeno una fonte
    if not (cfg.scope.repos or cfg.scope.teams or cfg.scope.topics):
        raise ValueError("scope must define at least one of: repos, teams, topics")

    # Ritorna dict per retrocompatibilità (il resto del codice usa dict access)
    return cfg.model_dump(by_alias=True)


def resolve_repos(scope: dict) -> list[str]:
    """Risolve scope → lista repo effective (repos + teams + topics)."""
    repos = list(scope.get("repos", []))
    # teams/topics richiedono gh CLI — best effort
    for team in scope.get("teams", []):
        try:
            org, slug = team.split("/", 1)
            result = subprocess.run(
                ["gh", "api", f"orgs/{org}/teams/{slug}/repos", "--jq", ".[].full_name"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                repos.extend(result.stdout.strip().split("\n"))
        except Exception as e:
            log.warning("failed to resolve team %s: %s", team, e)

    for topic in scope.get("topics", []):
        try:
            result = subprocess.run(
                ["gh", "search", "repos", "--topic", topic, "--json", "nameWithOwner",
                 "--jq", ".[].nameWithOwner"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
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

    # Default bot exclusion (module-level const) + config user
    excluded = DEFAULT_BOT_EXCLUDE | set(cfg.get("developers", {}).get("exclude", []))
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
    verification_override: dict[str, float] = {}
    if source_report.s3_devforge:
        events = ct.fetch_devforge_logs(since, until)
        if events:
            # Override Q4 con telemetry (più accurate di commit trailer grep)
            verification_override = ct.verification_rate_from_events(events)
            if verification_override:
                log.info("S3 verification_rate override applied for %d devs",
                         len(verification_override))

    if source_report.s3_blend:
        costs = ct.fetch_blend_usage(since, until)
        cost_scores = ct.normalize_cost_score(costs)

    # Compute KPIs
    window_tuple = (since, until)
    if prs_df.empty and commits_df.empty:
        log.warning("no data to compute")
        kpis_df = pd.DataFrame()
    else:
        kpis_df = ck.compute_all(
            prs_df, commits_df, tags_df, window_tuple,
            cost_scores=cost_scores,
            verification_override=verification_override or None,
        )

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
