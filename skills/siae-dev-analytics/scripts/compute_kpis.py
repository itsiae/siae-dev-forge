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
