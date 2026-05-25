"""Unit test per lib/release_risk/schema.py."""
from lib.release_risk.schema import (
    CriterionResult, ScoreCard, GenesisInfo, ReleaseRiskReport, SCHEMA_VERSION,
)


def test_criterion_result_construct():
    cr = CriterionResult(id=1, name="DB change", status="YES", weight=3, evidence=["file.sql"])
    assert cr.id == 1
    assert cr.status == "YES"
    assert cr.weight == 3


def test_scorecard_construct_partial():
    sc = ScoreCard(total_score=7, level="MEDIUM", decision="GO_WITH_MONITORING",
                   decision_rationale="...", partial=True, suggested_followups=["siae-security"])
    assert sc.partial is True
    assert "siae-security" in sc.suggested_followups


def test_genesis_info_declined():
    gi = GenesisInfo(merge_commits=[], declined=True)
    assert gi.declined is True
    assert gi.anomaly is None
    assert gi.user_confirmed is None


def test_genesis_info_all_confirmed():
    gi = GenesisInfo(
        merge_commits=[{"sha": "abc", "subject": "Merge", "feature_branch": "f1"}],
        user_confirmed=["f1"],
        unexpected=[],
        anomaly=False,
    )
    assert gi.anomaly is False


def test_report_roundtrip_json():
    sc = ScoreCard(total_score=5, level="MEDIUM", decision="GO_WITH_MONITORING", decision_rationale="r")
    gi = GenesisInfo(merge_commits=[], no_merges_found=True)
    report = ReleaseRiskReport(
        service="sport-test-service",
        release_branch="release/1.0.0",
        target_branch="main",
        diff_hash="abc123def456",
        baseline_main_sha="1a2b3c4d",
        diff_summary={"files_changed": 5},
        identification={"version": "1.0.0", "jira_tickets": ["SPORT-100"]},
        genesis=gi,
        criteria=[CriterionResult(id=1, name="DB", status="YES", weight=3)],
        scorecard=sc,
        generated_at="2026-05-14T10:00:00Z",
        output_path="docs/releases/2026-05-14-test.md",
        trigger="manual",
    )
    j = report.to_json()
    parsed = ReleaseRiskReport.from_json(j)
    assert parsed.service == "sport-test-service"
    assert parsed.scorecard.level == "MEDIUM"
    assert parsed.criteria[0].weight == 3
    assert parsed.genesis.no_merges_found is True


def test_schema_version_constant():
    assert SCHEMA_VERSION == "1.0"
