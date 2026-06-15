"""TDD — wiring CLI: _maybe_publish_confluence (auto-publish opt-in, fail-open)."""
import types

from lib.release_risk import cli
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)

_ENV_KEYS = ["DEVFORGE_CONFLUENCE_BASE_URL", "DEVFORGE_CONFLUENCE_EMAIL",
             "DEVFORGE_CONFLUENCE_API_TOKEN"]


def _report():
    return ReleaseRiskReport(
        service="sport-gestione-licenze-service", release_branch="release/2.14.0",
        target_branch="main", diff_hash="deadbeef", baseline_main_sha="1a2b3c4d",
        diff_summary={"files_changed": 5},
        identification={"version": "2.14.0", "owner": "team-x",
                        "date": "2026-06-15T10:00:00Z"},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=[CriterionResult(id=1, name="DB", status="YES", weight=3)],
        scorecard=ScoreCard(total_score=6, level="MEDIUM",
                            decision="GO_WITH_MONITORING", decision_rationale="r"),
        generated_at="2026-06-15T10:00:00Z", output_path="docs/releases/x.md",
    )


def _args(**kw):
    ns = types.SimpleNamespace(no_publish_confluence=False)
    ns.__dict__.update(kw)
    return ns


def _set_env(monkeypatch):
    monkeypatch.setenv("DEVFORGE_CONFLUENCE_BASE_URL", "https://siae-portfolio.atlassian.net/wiki")
    monkeypatch.setenv("DEVFORGE_CONFLUENCE_EMAIL", "tech@siae.it")
    monkeypatch.setenv("DEVFORGE_CONFLUENCE_API_TOKEN", "T")


def test_none_when_env_absent(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    assert cli._maybe_publish_confluence(_report(), _args()) is None


def test_none_when_flag_disables(monkeypatch):
    _set_env(monkeypatch)
    assert cli._maybe_publish_confluence(_report(), _args(no_publish_confluence=True)) is None


def test_calls_publish_with_storage_and_title(monkeypatch):
    _set_env(monkeypatch)
    captured = {}

    def fake_publish(report, storage, title, cfg, http_fn=None):
        captured["storage"] = storage
        captured["title"] = title
        return {"published": True, "action": "created", "url": "u", "reason": None}

    monkeypatch.setattr(cli, "publish_scorecard", fake_publish)
    res = cli._maybe_publish_confluence(_report(), _args())
    assert res["published"] is True
    assert res["action"] == "created"
    # storage XHTML reale, titolo deterministico con data + servizio
    assert "Release Risk Scorecard" in captured["storage"]
    assert "<h1>" in captured["storage"]
    assert captured["title"] == "15-06-2026 — sport-gestione-licenze-service v2.14.0"


def test_fail_open_when_publish_raises(monkeypatch):
    _set_env(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(cli, "publish_scorecard", boom)
    res = cli._maybe_publish_confluence(_report(), _args())
    assert res["published"] is False
    assert res["action"] == "error"
