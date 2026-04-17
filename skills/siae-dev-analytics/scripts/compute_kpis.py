"""Compute 11 KPI + z-score + ROI Index per sviluppatore.

KPI Velocity: V1-V5 (DORA + DX AI).
KPI Quality: Q1-Q6.
ROI Index: (velocity_score x quality_score) / cost_score.
"""
from __future__ import annotations

import hashlib
import re
import statistics
from datetime import datetime
import pandas as pd

SIAE_TAG_REGEX = re.compile(r"^(COLLAUDO|CERTIFICAZIONE|PRODUZIONE)[-_/].+$", re.IGNORECASE)

VELOCITY_KPIS = [
    "pr_cycle_time_p50",
    "lead_time_to_merge_p50",
    "pr_throughput_weekly",
    "time_to_first_review_p50",
    "deploy_frequency_monthly",
]

QUALITY_KPIS = [
    "review_comments_p50",
    "rework_ratio",
    "test_presence_rate",
    "verification_rate",
    "design_driven_rate",
    "revert_rate",
]


# ────────────────────────────────────────────────────────
# Velocity KPI
# ────────────────────────────────────────────────────────

def kpi_pr_cycle_time_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V1: median(merged_at - opened_at) in ore, per dev."""
    return prs.groupby("author")["cycle_time_hours"].median().to_dict()


def kpi_lead_time_to_merge_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V2: median(merged_at - first_commit_at) in ore."""
    return prs.groupby("author")["lead_time_hours"].median().to_dict()


def _weeks_in_window(window: tuple[str, str]) -> float:
    start, end = (datetime.fromisoformat(w) for w in window)
    return max((end - start).days / 7, 1e-9)


def kpi_pr_throughput_weekly(prs: pd.DataFrame, window: tuple[str, str]) -> dict[str, float]:
    """V3: count(merged_pr) / weeks_in_window."""
    weeks = _weeks_in_window(window)
    counts = prs.groupby("author").size()
    return (counts / weeks).to_dict()


def kpi_time_to_first_review_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V4: median(first_review_at - opened_at)."""
    s = prs.groupby("author")["time_to_first_review_hours"].median()
    return s.fillna(0).to_dict()


def _months_in_window(window: tuple[str, str]) -> float:
    """Mese = 30 giorni esatti (semplificazione reportistica).

    Scelta deliberata per coerenza test (30gg -> 1.0 mese esatto) e
    intuitivita' report. Differenza da 30.44gg e' < 1.5% -- trascurabile
    alla granularita' di ROI mensile.
    """
    start, end = (datetime.fromisoformat(w) for w in window)
    return max((end - start).days / 30, 1e-9)


def kpi_deploy_frequency_monthly(tags: pd.DataFrame, window: tuple[str, str]) -> dict[str, float]:
    """V5: count(tag per dev) / months_in_window."""
    if tags.empty or "attributed_to" not in tags.columns:
        return {}
    months = _months_in_window(window)
    # Filtra solo tag SIAE
    mask = tags["tag_name"].apply(lambda n: bool(SIAE_TAG_REGEX.match(n or "")))
    filtered = tags[mask]
    counts = filtered.groupby("attributed_to").size()
    return (counts / months).to_dict()


# ────────────────────────────────────────────────────────
# Quality KPI
# ────────────────────────────────────────────────────────

def kpi_review_comments_p50(prs: pd.DataFrame) -> dict[str, float]:
    """Q1: median(review_comments per PR)."""
    return prs.groupby("author")["review_comments"].median().to_dict()


def kpi_rework_ratio(prs: pd.DataFrame) -> dict[str, float]:
    """Q2: force_push_after_review / total_pr.

    DEFERRED in v1: GitHub GraphQL non espone direttamente force push events senza
    polling del timeline REST (costo alto). In v1 ritorna 0.0 per tutti gli autori
    e il report lo dichiara "N/A v1" in kpi-catalog.md.

    v2 roadmap: implementare fallback `commits_after_first_review / total_pr`
    contando commit pushati dopo il timestamp della prima review (campo gia'
    presente in reviews/createdAt e commits/committedDate).
    """
    if "force_pushes_after_review" not in prs.columns:
        return {a: 0.0 for a in prs["author"].unique()}
    grouped = prs.groupby("author").agg(
        fp=("force_pushes_after_review", "sum"),
        total=("author", "size"),
    )
    return (grouped["fp"] / grouped["total"]).to_dict()


def kpi_test_presence_rate(prs: pd.DataFrame) -> dict[str, float]:
    """Q3: PR con test files / tot PR."""
    return prs.groupby("author")["has_tests"].mean().to_dict()


def kpi_verification_rate(commits: pd.DataFrame) -> dict[str, float]:
    """Q4: commit con trailer verified-by / tot commit."""
    return commits.groupby("author")["has_verified_trailer"].mean().to_dict()


def kpi_design_driven_rate(prs: pd.DataFrame) -> dict[str, float]:
    """Q5: PR con link docs/plans design / tot PR."""
    return prs.groupby("author")["has_design_link"].mean().to_dict()


def kpi_revert_rate(commits: pd.DataFrame) -> dict[str, float]:
    """Q6: commit revert / tot commit."""
    return commits.groupby("author")["is_revert"].mean().to_dict()


# ────────────────────────────────────────────────────────
# In-Flight KPI (IF1-IF6) — v2
# ────────────────────────────────────────────────────────

def kpi_open_prs_count(prs: pd.DataFrame) -> dict[str, int]:
    """IF1: Count of OPEN PRs per author."""
    if prs.empty:
        return {}
    open_prs = prs[prs["state"] == "OPEN"]
    if open_prs.empty:
        return {}
    return open_prs.groupby("author").size().to_dict()


def kpi_draft_prs_count(prs: pd.DataFrame) -> dict[str, int]:
    """IF2: Count of draft PRs per author (OPEN + isDraft)."""
    if prs.empty:
        return {}
    drafts = prs[(prs["state"] == "OPEN") & (prs["is_draft"] == True)]  # noqa: E712
    if drafts.empty:
        return {}
    return drafts.groupby("author").size().to_dict()


def kpi_stuck_prs_count(prs: pd.DataFrame, threshold_days: int = 7) -> dict[str, int]:
    """IF3: Count of stuck PRs per author (OPEN + not updated > threshold_days)."""
    if prs.empty:
        return {}
    stuck = prs[prs["is_stuck"] == True]  # noqa: E712
    if stuck.empty:
        return {}
    return stuck.groupby("author").size().to_dict()


def kpi_closed_unmerged_count(prs: pd.DataFrame) -> dict[str, int]:
    """IF4: Count of closed-but-not-merged PRs per author."""
    if prs.empty:
        return {}
    closed_unmerged = prs[(prs["state"] == "CLOSED") & (prs["merged_at"].isna())]
    if closed_unmerged.empty:
        return {}
    return closed_unmerged.groupby("author").size().to_dict()


def kpi_reopen_count(prs: pd.DataFrame) -> dict[str, int]:
    """IF5: Total reopen events per author."""
    if prs.empty:
        return {}
    reopened = prs[prs["reopen_count"] > 0]
    if reopened.empty:
        return {}
    return reopened.groupby("author")["reopen_count"].sum().to_dict()


def kpi_oldest_open_pr_age_days(prs: pd.DataFrame) -> dict[str, float]:
    """IF6: Age in days of the oldest open PR per author."""
    if prs.empty:
        return {}
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    open_prs = prs[prs["state"] == "OPEN"].copy()
    if open_prs.empty:
        return {}
    open_prs["age_days"] = open_prs["created_at"].apply(
        lambda s: (now - pd.Timestamp(s)).days if pd.notna(s) else 0
    )
    return open_prs.groupby("author")["age_days"].max().to_dict()


# ────────────────────────────────────────────────────────
# z-score + ROI
# ────────────────────────────────────────────────────────

def z_score(values: dict[str, float]) -> dict[str, float]:
    """Z-score normalizzato. Edge: N<2 o sigma=0 -> 0."""
    vs = [v for v in values.values() if v is not None and not pd.isna(v)]
    if len(vs) < 2:
        return {k: 0.0 for k in values}
    mean = statistics.mean(vs)
    # Population std (pstdev, N) — coerente con z-score classico usato nei test.
    # Diverso da stdev (sample, N-1) che richiede N>=2 comunque gestito sopra.
    std = statistics.pstdev(vs) if len(vs) > 1 else 0
    if std == 0:
        return {k: 0.0 for k in values}
    return {k: (v - mean) / std if v is not None and not pd.isna(v) else 0.0
            for k, v in values.items()}


def roi_index(velocity_score: float, quality_score: float, cost_score: float = 1.0) -> float:
    """ROI = (velocity x quality) / cost."""
    if cost_score == 0:
        return 0.0
    return (velocity_score * quality_score) / cost_score


# ────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────

def compute_all(
    prs: pd.DataFrame,
    commits: pd.DataFrame,
    tags: pd.DataFrame,
    window: tuple[str, str],
    cost_scores: dict[str, float] | None = None,
    verification_override: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calcola tutti i KPI + score + ROI per ogni dev.

    Se `verification_override` è fornito (da S3 devforge-logs in FULL/HYBRID mode),
    sostituisce il valore di Q4 calcolato da commit message trailer con la source
    superior accuracy dagli eventi telemetry.
    """
    # Q4: preferisci S3 telemetry se disponibile (merge con trailer fallback)
    if verification_override:
        q4 = {**kpi_verification_rate(commits), **verification_override}
    else:
        q4 = kpi_verification_rate(commits)

    kpis = {
        "pr_cycle_time_p50": kpi_pr_cycle_time_p50(prs),
        "lead_time_to_merge_p50": kpi_lead_time_to_merge_p50(prs),
        "pr_throughput_weekly": kpi_pr_throughput_weekly(prs, window),
        "time_to_first_review_p50": kpi_time_to_first_review_p50(prs),
        "deploy_frequency_monthly": kpi_deploy_frequency_monthly(tags, window),
        "review_comments_p50": kpi_review_comments_p50(prs),
        "rework_ratio": kpi_rework_ratio(prs),
        "test_presence_rate": kpi_test_presence_rate(prs),
        "verification_rate": q4,
        "design_driven_rate": kpi_design_driven_rate(prs),
        "revert_rate": kpi_revert_rate(commits),
    }

    all_devs = set()
    for v in kpis.values():
        all_devs.update(v.keys())

    df = pd.DataFrame(index=sorted(all_devs))
    for name, values in kpis.items():
        df[name] = pd.Series(values)
    df = df.fillna(0)

    # Velocity score: piu' basso cycle_time = meglio -> invertiamo segno dove serve
    # Semplice media z-score delle velocity (throughput e deploy_freq piu' alto = meglio;
    # cycle/lead/review_time piu' basso = meglio -> segno opposto)
    velocity_inverted = {"pr_cycle_time_p50", "lead_time_to_merge_p50", "time_to_first_review_p50"}
    velocity_z = []
    for kpi in VELOCITY_KPIS:
        zs = z_score(df[kpi].to_dict())
        if kpi in velocity_inverted:
            zs = {k: -v for k, v in zs.items()}
        velocity_z.append(pd.Series(zs))
    df["velocity_score"] = pd.concat(velocity_z, axis=1).mean(axis=1)

    # Quality score: rework/revert/review_comments piu' basso = meglio; test/verification/design piu' alto = meglio
    quality_inverted = {"review_comments_p50", "rework_ratio", "revert_rate"}
    quality_z = []
    for kpi in QUALITY_KPIS:
        zs = z_score(df[kpi].to_dict())
        if kpi in quality_inverted:
            zs = {k: -v for k, v in zs.items()}
        quality_z.append(pd.Series(zs))
    df["quality_score"] = pd.concat(quality_z, axis=1).mean(axis=1)

    # ROI
    cost_scores = cost_scores or {d: 1.0 for d in df.index}
    df["roi_index"] = [
        roi_index(df.loc[d, "velocity_score"], df.loc[d, "quality_score"], cost_scores.get(d, 1.0))
        for d in df.index
    ]

    return df


# ────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────

def filter_by_min_commits(commits: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
    """Esclude dev con meno di threshold commit."""
    counts = commits.groupby("author").size()
    keep = counts[counts >= threshold].index
    return commits[commits["author"].isin(keep)]


def anonymize_login(login: str) -> str:
    """SHA256[:8] -- deterministico."""
    return hashlib.sha256(login.encode()).hexdigest()[:8]


# ────────────────────────────────────────────────────────
# DevForge Adoption KPI (DA1-DA3) — v2
# ────────────────────────────────────────────────────────

def kpi_devforge_skill_invocation_rate(
    skill_invocations_by_dev: dict[str, int],
    weeks_in_window: float,
) -> dict[str, float]:
    """DA1: skill invocations / week per dev."""
    if weeks_in_window <= 0:
        return {}
    return {dev: count / weeks_in_window for dev, count in skill_invocations_by_dev.items()}


def kpi_claude_session_density(
    session_starts_by_dev: dict[str, int],
    working_days: int,
) -> dict[str, float]:
    """DA2: sessions / working day per dev."""
    if working_days <= 0:
        return {}
    return {dev: count / working_days for dev, count in session_starts_by_dev.items()}


def kpi_siae_brainstorming_before_coding(
    prs: pd.DataFrame,
    docs_plans_dir: "Path",
    threshold_hours: int = 24,
) -> dict[str, float]:
    """DA3: % PR con design doc creato < 24h prima del primo commit / total PR per dev."""
    if prs.empty:
        return {}
    from pathlib import Path
    if not Path(docs_plans_dir).exists():
        return {a: 0.0 for a in prs["author"].unique()}
    # v2: se PR ha design_link, considera disciplinato
    return prs.groupby("author")["has_design_link"].mean().to_dict()


# ────────────────────────────────────────────────────────
# Commit type parser (task-07)
# ────────────────────────────────────────────────────────

COMMIT_TYPE_RE = re.compile(r"^(feat|fix|refactor|perf|test|docs|chore|build|ci|style)(\([^)]+\))?:", re.MULTILINE)


def extract_commit_type(message: str) -> str | None:
    """Extract conventional commit type from message."""
    m = COMMIT_TYPE_RE.search(message or "")
    return m.group(1).lower() if m else None


# ────────────────────────────────────────────────────────
# Cost KPI (C1-C4) — task-07
# ────────────────────────────────────────────────────────

def kpi_eur_per_merged_pr(cost_by_dev: dict[str, float], merged_pr_count: dict[str, int]) -> dict[str, float]:
    """C1: EUR spent / merged PRs per dev."""
    result = {}
    for dev, cost in cost_by_dev.items():
        prs = merged_pr_count.get(dev, 0)
        if prs > 0:
            result[dev] = cost / prs
    return result


def kpi_eur_per_accepted_loc(cost_by_dev: dict, net_loc_by_dev: dict) -> dict[str, float]:
    """C2: EUR / net LOC shipped per dev."""
    result = {}
    for dev, cost in cost_by_dev.items():
        loc = net_loc_by_dev.get(dev, 0)
        if loc > 0:
            result[dev] = cost / loc
    return result


def kpi_tokens_per_completed_pr(tokens_by_dev: dict, merged_pr_count: dict) -> dict[str, float]:
    """C3: tokens consumed / merged PRs per dev."""
    result = {}
    for dev, tok in tokens_by_dev.items():
        prs = merged_pr_count.get(dev, 0)
        if prs > 0:
            result[dev] = tok / prs
    return result


def kpi_cost_per_story_point(cost_by_dev: dict, sp_closed: dict) -> dict[str, float]:
    """C4: EUR / story points closed per dev."""
    result = {}
    for dev, cost in cost_by_dev.items():
        sp = sp_closed.get(dev, 0)
        if sp > 0:
            result[dev] = cost / sp
    return result


# ────────────────────────────────────────────────────────
# Value KPI (VA1-VA7) — task-07
# ────────────────────────────────────────────────────────

def kpi_features_shipped(commits: pd.DataFrame) -> dict[str, int]:
    """VA1: count feat commits per dev."""
    if commits.empty:
        return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    feat = commits[commits["type"] == "feat"]
    return feat.groupby("author").size().to_dict()


def kpi_bugs_fixed(commits: pd.DataFrame) -> dict[str, int]:
    """VA2: count fix commits per dev."""
    if commits.empty:
        return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    fix = commits[commits["type"] == "fix"]
    return fix.groupby("author").size().to_dict()


def kpi_tech_debt_reduced(commits: pd.DataFrame) -> dict[str, int]:
    """VA3: count refactor+perf commits per dev."""
    if commits.empty:
        return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    td = commits[commits["type"].isin(["refactor", "perf"])]
    return td.groupby("author").size().to_dict()


def kpi_net_loc_shipped(prs: pd.DataFrame) -> dict[str, int]:
    """VA4: net LOC (additions - deletions) per dev."""
    if prs.empty or "additions" not in prs.columns:
        return {}
    prs = prs.copy()
    prs["net"] = prs["additions"] - prs["deletions"]
    return prs.groupby("author")["net"].sum().to_dict()


def kpi_compliance_bundle_rate(prs: pd.DataFrame, commits: pd.DataFrame) -> dict[str, float]:
    """VA5: PR con (test + design link + verified-by) / total."""
    if prs.empty:
        return {}
    prs = prs.copy()
    if commits.empty or "has_verified_trailer" not in commits.columns:
        prs["bundled"] = prs["has_tests"] & prs["has_design_link"]
    else:
        verif_by_dev = commits.groupby("author")["has_verified_trailer"].any().to_dict()
        prs["has_verified"] = prs["author"].map(verif_by_dev).fillna(False)
        prs["bundled"] = prs["has_tests"] & prs["has_design_link"] & prs["has_verified"]
    return prs.groupby("author")["bundled"].mean().to_dict()


def kpi_first_shot_quality(prs: pd.DataFrame) -> dict[str, float]:
    """VA6: PR senza force-push post first review / total."""
    if prs.empty:
        return {}
    col = "force_push_after_review" if "force_push_after_review" in prs.columns else None
    if col is None:
        return {a: 1.0 for a in prs["author"].unique()}
    prs = prs.copy()
    prs["no_rework"] = ~prs[col]
    return prs.groupby("author")["no_rework"].mean().to_dict()


def kpi_design_adherence_rate(prs: pd.DataFrame) -> dict[str, float]:
    """VA7: design-driven rate (has_design_link)."""
    if prs.empty:
        return {}
    return prs.groupby("author")["has_design_link"].mean().to_dict()


# ────────────────────────────────────────────────────────
# Delivery KPI (D1-D4) DORA extended — task-07
# ────────────────────────────────────────────────────────

def kpi_time_to_production_p50(tags: pd.DataFrame, prs: pd.DataFrame) -> dict[str, float]:
    """D1: median(tag PRODUZIONE_date - PR merge_date) per dev."""
    if tags.empty or prs.empty:
        return {}
    prod_tags = tags[tags["tag_name"].str.contains("PRODUZIONE", case=False, na=False)]
    if prod_tags.empty:
        return {}
    return {}  # Richiede join commit_oid → PR — simplified per v2


def kpi_change_failure_rate(commits: pd.DataFrame, deploy_window_days: int = 7) -> dict[str, float]:
    """D2: DORA CFR proxy — revert count / total commits per dev."""
    if commits.empty:
        return {}
    result = {}
    for dev in commits["author"].unique():
        dev_commits = commits[commits["author"] == dev]
        dev_reverts = len(dev_commits[dev_commits["is_revert"] == True])  # noqa: E712
        total = len(dev_commits)
        if total > 0:
            result[dev] = dev_reverts / total
    return result


def kpi_incident_free_days(commits: pd.DataFrame) -> int:
    """D3: Days since last revert globally."""
    if commits.empty:
        return 0
    reverts = commits[commits["is_revert"] == True]  # noqa: E712
    if reverts.empty:
        return 999  # no reverts ever (cap)
    last_revert = pd.Timestamp(reverts["committed_at"].max())
    now = pd.Timestamp.now(tz="UTC")
    return max(0, (now - last_revert).days)


def kpi_deploy_lead_time_p50(commits: pd.DataFrame, tags: pd.DataFrame) -> dict[str, float]:
    """D4: median(commit → PROD tag) per dev. Richiede join commit ↔ tag."""
    if commits.empty or tags.empty:
        return {}
    return {}  # Simplified per v2


# ────────────────────────────────────────────────────────
# ROI v2 Index
# ────────────────────────────────────────────────────────

def kpi_roi_v2_index(
    features_shipped: dict,
    complexity_weight_by_dev: dict,
    compliance_rate_by_dev: dict,
    cost_by_dev: dict,
    seasonality_adj: float,
) -> dict:
    """roi_v2 = (features * complexity * compliance) / (cost * seasonality_adj)."""
    from validators import assert_finite
    result = {}
    if seasonality_adj <= 0:
        seasonality_adj = 1.0
    for dev in set(features_shipped) | set(cost_by_dev):
        feat = features_shipped.get(dev, 0)
        cw = complexity_weight_by_dev.get(dev, 1.0)
        cr = compliance_rate_by_dev.get(dev, 0.0)
        cost = cost_by_dev.get(dev, 1.0) or 1.0
        value = feat * cw * cr
        roi = value / (cost * seasonality_adj)
        assert_finite(roi, f"roi_v2[{dev}]")
        result[dev] = roi
    return result
