"""TDD — render_scorecard_storage: ReleaseRiskReport → Confluence storage XHTML.

Genera storage XHTML DIRETTO dal report (no markdown→storage), così si evita
il bug noto del blockquote-con-heading (`> ## ...`) che si perde in conversione.
"""
from lib.release_risk.renderer import render_scorecard_storage
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)


def _make_report(level="LOW", score=2, decision="GO", service="sport-test-service",
                 criteria=None, version="1.0.0"):
    return ReleaseRiskReport(
        service=service,
        release_branch="release/1.0.0",
        target_branch="main",
        diff_hash="abc123",
        baseline_main_sha="1a2b3c4d",
        diff_summary={"files_changed": 5},
        identification={"version": version, "owner": "team-x"},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=criteria or [CriterionResult(id=1, name="DB change", status="YES",
                                              weight=3, evidence=["ALTER TABLE X"])],
        scorecard=ScoreCard(total_score=score, level=level, decision=decision,
                            decision_rationale="rationale-text"),
        generated_at="2026-05-14T10:00:00Z",
        output_path="docs/releases/2026-05-14-test.md",
    )


def test_storage_has_h1_and_title():
    html = render_scorecard_storage(_make_report())
    assert "<h1>" in html
    assert "Release Risk Scorecard" in html
    assert "sport-test-service" in html


def test_storage_contains_verdict_not_lost():
    # Il blocco verdetto (level/score/decision) DEVE essere presente — è la regressione
    # che vogliamo evitare (blockquote-con-heading droppato in conversione).
    html = render_scorecard_storage(_make_report(level="MEDIUM", score=7,
                                                  decision="GO_WITH_MONITORING"))
    assert "MEDIUM" in html
    assert "7" in html
    assert "GO_WITH_MONITORING" in html
    assert "rationale-text" in html


def test_storage_renders_tables():
    html = render_scorecard_storage(_make_report())
    assert "<table" in html
    assert "<th>" in html and "<td>" in html
    # criteri
    assert "DB change" in html


def test_storage_escapes_html_special_chars():
    html = render_scorecard_storage(_make_report(service="a<b>&\"c"))
    assert "&lt;b&gt;" in html
    assert "&amp;" in html
    # niente tag iniettato grezzo dal contenuto dinamico
    assert "<b>" not in html


def test_storage_is_wellformed_xhtml():
    import xml.etree.ElementTree as ET
    html = render_scorecard_storage(_make_report(level="CRITICAL", score=18,
                                                  decision="NO_GO_WITHOUT_CAB"))
    # storage format deve essere XML ben formato (wrappo in root per il parse)
    ET.fromstring(f"<root>{html}</root>")


def test_storage_includes_diff_hash_for_traceability():
    html = render_scorecard_storage(_make_report())
    assert "abc123" in html
