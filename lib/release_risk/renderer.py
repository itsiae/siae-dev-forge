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

    # Razionale del rilascio (contesto funzionale per TechOps)
    if report.narrative:
        lines.append("## 📝 Razionale del rilascio")
        lines.append("")
        lines.append(report.narrative)
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


def _esc(value) -> str:
    """HTML-escape per il contenuto dinamico inserito nello storage XHTML."""
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


_NEXT_ACTIONS_STORAGE = {
    "LOW": "GO deploy standard. Monitoring standard.",
    "MEDIUM": "Notifica team + monitoring 2h post-deploy. Rollback plan verificato.",
    "HIGH": "POSTPONE senza approval. War room 4h + TL+Ops approval prima di deploy.",
    "CRITICAL": "STOP. CAB approval obbligatoria. Deploy solo fuori orario (weekend/notte).",
}


def render_scorecard_storage(report: ReleaseRiskReport) -> str:
    """Render ReleaseRiskReport → Confluence storage XHTML.

    Genera lo storage DIRETTAMENTE dal report (no markdown→storage), così si
    evita il bug del blockquote-con-heading (`> ## ...`) che viene droppato in
    conversione. Il contenuto dinamico è sempre HTML-escaped; l'output è XML
    ben formato (tabelle/heading/paragrafi standard accettati dallo storage).
    """
    sc = report.scorecard
    level_emoji = LEVEL_EMOJI[sc.level]
    p = []

    p.append(f"<h1>{level_emoji} Release Risk Scorecard — {_esc(report.service)}</h1>")

    # Metadati
    p.append("<table><tbody>")
    p.append(f"<tr><th>Release branch</th><td><code>{_esc(report.release_branch)}</code> "
             f"→ <code>{_esc(report.target_branch)}</code></td></tr>")
    p.append(f"<tr><th>Generated</th><td>{_esc(report.generated_at)}</td></tr>")
    p.append(f"<tr><th>Diff hash</th><td><code>{_esc(report.diff_hash)}</code></td></tr>")
    p.append(f"<tr><th>Baseline main SHA</th><td><code>"
             f"{_esc(report.baseline_main_sha or 'N/A (first release)')}</code></td></tr>")
    p.append("</tbody></table>")

    # Verdetto (heading + paragrafo: NON blockquote-con-heading)
    p.append(f"<h2>{level_emoji} Level: {_esc(sc.level)} | Score: {sc.total_score}/36 "
             f"| Decision: {_esc(sc.decision)}</h2>")
    p.append(f"<p><em>{_esc(sc.decision_rationale)}</em></p>")
    if sc.partial:
        p.append("<p><strong>⚠️ PARTIAL SCORECARD</strong> — alcuni criteri = "
                 "REQUIRES_INPUT. Verifica manuale richiesta pre-deploy.</p>")
    if sc.suggested_followups:
        fu = ", ".join(_esc(f) for f in sc.suggested_followups)
        p.append(f"<p><strong>📌 SUGGESTED FOLLOW-UP:</strong> {fu}</p>")

    # Razionale del rilascio (contesto funzionale per TechOps)
    if report.narrative:
        p.append("<h2>📝 Razionale del rilascio</h2>")
        p.append(f"<p>{_esc(report.narrative)}</p>")

    # Identificazione
    p.append("<h2>📋 Identificazione</h2>")
    p.append("<table><tbody><tr><th>Campo</th><th>Valore</th></tr>")
    for k, v in report.identification.items():
        p.append(f"<tr><td><strong>{_esc(k)}</strong></td><td>{_esc(v)}</td></tr>")
    p.append("</tbody></table>")

    # Genesis
    p.append("<h2>🌱 Release Genesis</h2>")
    g = report.genesis
    if g.no_merges_found:
        p.append("<p><em>Release branch built linearly (no feature-branch merges).</em></p>")
    elif g.declined:
        p.append("<p>⚠️ Genesis NON confermato dall'utente. Verifica manuale pre-deploy.</p>")
    else:
        p.append(f"<p><strong>Feature confermate:</strong> {_esc(g.user_confirmed or 'N/A')}</p>")
        if g.unexpected:
            p.append(f"<p><strong>Feature non attese (anomaly):</strong> {_esc(g.unexpected)}</p>")

    # Fattori di rischio
    p.append("<h2>🔴 Fattori di Rischio (18 criteri)</h2>")
    p.append("<table><tbody><tr><th>#</th><th>Criterio</th><th>Status</th>"
             "<th>Peso</th><th>Evidence</th></tr>")
    for c in sorted(report.criteria, key=lambda c: c.id):
        emoji = _criterion_emoji(c)
        ev = "; ".join(c.evidence[:3]) if c.evidence else "—"
        if len(ev) > 80:
            ev = ev[:77] + "..."
        p.append(f"<tr><td>{c.id}</td><td><strong>{_esc(c.name)}</strong></td>"
                 f"<td>{emoji} {_esc(c.status)}</td><td>{c.weight:+d}</td>"
                 f"<td>{_esc(ev)}</td></tr>")
    p.append("</tbody></table>")

    # Next actions
    p.append("<h2>➡️ Next Actions</h2>")
    p.append(f"<p>{_esc(_NEXT_ACTIONS_STORAGE[sc.level])}</p>")
    p.append(f"<p><em>Generato da DevForge · siae-release-risk · diff "
             f"<code>{_esc(report.diff_hash)}</code></em></p>")

    return "".join(p)
