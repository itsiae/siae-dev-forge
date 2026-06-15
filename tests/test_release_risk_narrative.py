"""TDD — sezione 'Razionale del rilascio + change funzionali' (contesto per TechOps).

Fonte ibrida: manual (--rationale) > PR body (hook) > derivato (Jira + feature branch).
Render in cima alla scorecard (dopo il verdetto), sia markdown che storage XHTML.
"""
import types

from lib.release_risk.narrative import build_narrative
from lib.release_risk import cli
from lib.release_risk.renderer import render_scorecard, render_scorecard_storage
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)


def _report(narrative=None, narrative_source=None):
    return ReleaseRiskReport(
        service="sport-x-service", release_branch="release/1.0.0", target_branch="main",
        diff_hash="abc123", baseline_main_sha="1a2b3c4d", diff_summary={"files_changed": 5},
        identification={"version": "1.0.0", "owner": "team-x"},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=[CriterionResult(id=1, name="DB", status="YES", weight=3)],
        scorecard=ScoreCard(total_score=6, level="MEDIUM",
                            decision="GO_WITH_MONITORING", decision_rationale="r"),
        generated_at="2026-06-15T10:00:00Z", output_path="docs/releases/x.md",
        narrative=narrative, narrative_source=narrative_source,
    )


# ---------- build_narrative: priorità ----------

def test_manual_rationale_has_top_priority():
    txt, src = build_narrative(rationale="Sblocca il pagamento licenze locali.",
                               pr_body="qualcosa", jira_tickets=["SPORT-1"])
    assert txt == "Sblocca il pagamento licenze locali."
    assert src == "manual"


def test_pr_body_used_when_no_manual():
    txt, src = build_narrative(pr_body="## Titolo\nIntroduce il nuovo flusso di conferma.")
    assert src == "pr-body"
    assert "nuovo flusso di conferma" in txt


def test_pr_body_strips_html_marker():
    txt, src = build_narrative(pr_body="<!-- release-risk:abc -->\nTesto reale del perché.")
    assert "release-risk:abc" not in txt
    assert "Testo reale del perché." in txt


def test_pr_body_truncated_with_ellipsis():
    long = "parola " * 300
    txt, src = build_narrative(pr_body=long)
    assert len(txt) <= 801
    assert txt.endswith("…")


def test_derived_from_jira_and_genesis():
    g = GenesisInfo(merge_commits=[{"sha": "a"}], user_confirmed=["feat/pagamenti"])
    txt, src = build_narrative(jira_tickets=["SPORT-9", "SPORT-2"], genesis=g, files_changed=12)
    assert src == "derived"
    assert "feat/pagamenti" in txt
    assert "SPORT-2" in txt and "SPORT-9" in txt   # ordinati
    assert "12 file" in txt


def test_none_when_nothing_available():
    txt, src = build_narrative(genesis=GenesisInfo(merge_commits=[]), files_changed=3)
    assert txt is None
    assert src is None


# ---------- renderer: sezione presente/assente ----------

def test_storage_renders_narrative_section_when_present():
    html = render_scorecard_storage(_report(narrative="Motivazione funzionale del rilascio.",
                                             narrative_source="manual"))
    assert "Razionale" in html
    assert "Motivazione funzionale del rilascio." in html


def test_storage_omits_narrative_section_when_absent():
    html = render_scorecard_storage(_report(narrative=None))
    assert "Razionale del rilascio" not in html


def test_storage_escapes_narrative():
    html = render_scorecard_storage(_report(narrative="a <b> & c", narrative_source="manual"))
    assert "&lt;b&gt;" in html and "&amp;" in html
    assert "<b>" not in html


def test_markdown_renders_narrative_section_when_present():
    md = render_scorecard(_report(narrative="Perché funzionale del rilascio.",
                                  narrative_source="pr-body"))
    assert "Razionale" in md
    assert "Perché funzionale del rilascio." in md


def test_markdown_omits_narrative_when_absent():
    md = render_scorecard(_report(narrative=None))
    assert "Razionale del rilascio" not in md


# ---------- cli seam: _resolve_narrative ----------

def _args(**kw):
    ns = types.SimpleNamespace(rationale=None, pr_body_file=None)
    ns.__dict__.update(kw)
    return ns


def test_resolve_narrative_manual(tmp_path):
    txt, src = cli._resolve_narrative(_args(rationale="Motivo X"), ["SPORT-1"],
                                      GenesisInfo(merge_commits=[]), 5)
    assert (txt, src) == ("Motivo X", "manual")


def test_resolve_narrative_from_pr_body_file(tmp_path):
    f = tmp_path / "pr.txt"
    f.write_text("Descrizione PR: introduce il consolidamento profili.")
    txt, src = cli._resolve_narrative(_args(pr_body_file=str(f)), [], None, 5)
    assert src == "pr-body"
    assert "consolidamento profili" in txt


def test_resolve_narrative_derived_fallback(tmp_path):
    g = GenesisInfo(merge_commits=[{"sha": "a"}], user_confirmed=["feat/y"])
    txt, src = cli._resolve_narrative(_args(), ["SPORT-7"], g, 4)
    assert src == "derived"
    assert "feat/y" in txt and "SPORT-7" in txt
