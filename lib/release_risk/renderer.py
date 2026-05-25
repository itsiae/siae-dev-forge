"""Render ReleaseRiskReport → markdown via template fill."""
from __future__ import annotations

from pathlib import Path
from lib.release_risk.schema import ReleaseRiskReport, CriterionResult

LEVEL_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
STATUS_EMOJI_POS_WEIGHT = {"YES": "❌", "NO": "✅", "REQUIRES_INPUT": "⚠️", "TOOL_UNAVAILABLE": "⚠️"}
STATUS_EMOJI_NEG_WEIGHT = {"YES": "✅", "NO": "❌", "REQUIRES_INPUT": "⚠️", "TOOL_UNAVAILABLE": "⚠️"}


def _criterion_emoji(c: CriterionResult) -> str:
    """Positive-weight: YES=risk-present=❌. Negative-weight (10, 13): YES=mitigation=✅."""
    table = STATUS_EMOJI_NEG_WEIGHT if c.weight < 0 else STATUS_EMOJI_POS_WEIGHT
    return table.get(c.status, "⚠️")


def render_scorecard(report: ReleaseRiskReport, idempotency_marker: str = "") -> str:
    """Render full scorecard markdown."""
    sc = report.scorecard
    level_emoji = LEVEL_EMOJI[sc.level]
    lines = []
    if idempotency_marker:
        lines.append(idempotency_marker)
        lines.append("")
    lines.append(f"# {level_emoji} Release Risk Scorecard — {report.service}")
    lines.append("")
    lines.append(f"**Release branch:** `{report.release_branch}` → `{report.target_branch}`")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Diff hash:** `{report.diff_hash}`")
    lines.append(f"**Baseline main SHA:** `{report.baseline_main_sha or 'N/A (first release)'}`")
    lines.append("")
    lines.append(f"## {level_emoji} Level: **{sc.level}** | Score: **{sc.total_score}/36** | Decision: **{sc.decision}**")
    lines.append("")
    lines.append(f"_{sc.decision_rationale}_")
    lines.append("")

    if sc.partial:
        lines.append("> ⚠️ **PARTIAL SCORECARD** — alcuni criteri = `REQUIRES_INPUT`. Verifica manuale richiesta pre-deploy.")
        lines.append("")

    if sc.suggested_followups:
        lines.append("> 📌 **SUGGESTED FOLLOW-UP**: " + ", ".join(f"`{f}`" for f in sc.suggested_followups))
        lines.append("> Esegui le skill suggerite per deep analysis prima di chiudere la release.")
        lines.append("")

    # Identification
    lines.append("## 📋 Identificazione")
    lines.append("")
    lines.append("| Campo | Valore |")
    lines.append("|---|---|")
    for k, v in report.identification.items():
        lines.append(f"| **{k}** | {v} |")
    lines.append("")

    # Genesis
    lines.append("## 🌱 Release Genesis")
    lines.append("")
    g = report.genesis
    if g.no_merges_found:
        lines.append("_Release branch built linearly (no feature-branch merges)._")
    elif g.declined:
        lines.append("> ⚠️ Genesis NON confermato dall'utente. Verifica manuale pre-deploy.")
    else:
        lines.append(f"**Feature confermate:** {g.user_confirmed or 'N/A'}")
        if g.unexpected:
            lines.append(f"**Feature non attese (anomaly):** {g.unexpected}")
    lines.append("")

    # Criteri table
    lines.append("## 🔴 Fattori di Rischio (18 criteri)")
    lines.append("")
    lines.append("| # | Criterio | Status | Peso | Evidence |")
    lines.append("|---|---|---|---|---|")
    for c in sorted(report.criteria, key=lambda c: c.id):
        emoji = _criterion_emoji(c)
        ev_short = "; ".join(c.evidence[:3]) if c.evidence else "—"
        if len(ev_short) > 80:
            ev_short = ev_short[:77] + "..."
        lines.append(f"| {c.id} | **{c.name}** | {emoji} {c.status} | {c.weight:+d} | {ev_short} |")
    lines.append("")

    # Next actions
    lines.append("## ➡️ Next Actions")
    lines.append("")
    next_actions = {
        "LOW": "✅ GO deploy standard. Monitoring standard.",
        "MEDIUM": "🟡 Notifica team + monitoring 2h post-deploy. Rollback plan verificato.",
        "HIGH": "🟠 POSTPONE senza approval. War room 4h + TL+Ops approval prima di deploy.",
        "CRITICAL": "🔴 STOP. CAB approval obbligatoria. Deploy solo fuori orario (weekend/notte).",
    }
    lines.append(next_actions[sc.level])
    lines.append("")
    lines.append(f"_Output saved at: `{report.output_path}`_")
    return "\n".join(lines)


def write_scorecard(report: ReleaseRiskReport, output_path: Path,
                    idempotency_marker: str = "") -> bool:
    """Atomic write scorecard md to output_path."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(".tmp")
        tmp.write_text(render_scorecard(report, idempotency_marker))
        import os
        os.replace(tmp, output_path)
        return True
    except Exception:
        return False
