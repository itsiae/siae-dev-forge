"""TDD — confluence_publish: pubblicazione scorecard su Confluence (token tecnico).

Auth: API token (Basic email:token) di un account tecnico → automazione anche headless/CI.
Idempotenza: una pagina per rilascio (find-by-title → create|update).
Fail-open: nessuna eccezione propagata; errori restituiti come dict.
HTTP injettabile (http_fn) per i test, come il pattern mcp_invoker di kg_lookup.
"""
import base64
import json

from lib.release_risk.confluence_publish import (
    ConfluenceConfig, config_from_env, build_page_title, publish_scorecard,
)
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)


def _make_report(service="sport-gestione-licenze-service", version="2.14.0"):
    return ReleaseRiskReport(
        service=service, release_branch="release/2.14.0", target_branch="main",
        diff_hash="deadbeef", baseline_main_sha="1a2b3c4d",
        diff_summary={"files_changed": 5},
        identification={"version": version, "owner": "team-x"},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=[CriterionResult(id=1, name="DB", status="YES", weight=3)],
        scorecard=ScoreCard(total_score=6, level="MEDIUM",
                            decision="GO_WITH_MONITORING", decision_rationale="r"),
        generated_at="2026-06-15T10:00:00Z",
        output_path="docs/releases/2026-06-15-x.md",
    )


def _cfg():
    return ConfluenceConfig(
        base_url="https://siae-portfolio.atlassian.net/wiki",
        email="tech@siae.it", api_token="TOKEN123",
        space_id="222527493", parent_id="670793729", space_key="TechOps",
    )


# ---------- config_from_env ----------

def test_config_from_env_none_when_missing():
    assert config_from_env({}) is None
    # manca il token → None
    assert config_from_env({
        "DEVFORGE_CONFLUENCE_BASE_URL": "https://x/wiki",
        "DEVFORGE_CONFLUENCE_EMAIL": "a@b.it",
    }) is None


def test_config_from_env_defaults_siae():
    cfg = config_from_env({
        "DEVFORGE_CONFLUENCE_BASE_URL": "https://siae-portfolio.atlassian.net/wiki/",
        "DEVFORGE_CONFLUENCE_EMAIL": "tech@siae.it",
        "DEVFORGE_CONFLUENCE_API_TOKEN": "T",
    })
    assert cfg is not None
    assert cfg.base_url == "https://siae-portfolio.atlassian.net/wiki"  # trailing slash strip
    assert cfg.space_key == "TechOps"
    assert cfg.space_id == "222527493"
    assert cfg.parent_id == "670793729"


# ---------- build_page_title ----------

def test_build_page_title_format():
    title = build_page_title(_make_report())
    assert title == "15-06-2026 — sport-gestione-licenze-service v2.14.0"


def test_build_page_title_omits_unknown_version():
    title = build_page_title(_make_report(version="unknown"))
    assert title == "15-06-2026 — sport-gestione-licenze-service"


# ---------- publish: create ----------

def test_publish_creates_when_not_existing():
    captured = {}

    def http_fn(method, url, headers, body, timeout):
        captured.setdefault("calls", []).append((method, url))
        if method == "GET" and "/api/v2/pages?" in url:
            return 200, {"results": []}
        if method == "POST" and url.endswith("/api/v2/pages"):
            payload = json.loads(body)
            assert payload["spaceId"] == "222527493"
            assert payload["parentId"] == "670793729"
            assert payload["body"]["representation"] == "storage"
            return 200, {"id": "999",
                         "_links": {"webui": "/spaces/TechOps/pages/999/Title"}}
        raise AssertionError(f"unexpected {method} {url}")

    res = publish_scorecard(_make_report(), "<p>x</p>", "T", _cfg(), http_fn=http_fn)
    assert res["published"] is True
    assert res["action"] == "created"
    assert res["url"].endswith("/spaces/TechOps/pages/999/Title")


# ---------- publish: update (idempotente) ----------

def test_publish_updates_when_existing_bumps_version():
    def http_fn(method, url, headers, body, timeout):
        if method == "GET" and "/api/v2/pages?" in url:
            return 200, {"results": [{"id": "42"}]}
        if method == "GET" and url.endswith("/api/v2/pages/42"):
            return 200, {"id": "42", "version": {"number": 3},
                         "_links": {"webui": "/spaces/TechOps/pages/42/T"}}
        if method == "PUT" and url.endswith("/api/v2/pages/42"):
            payload = json.loads(body)
            assert payload["version"]["number"] == 4  # bump 3→4
            assert payload["id"] == "42"
            return 200, {"id": "42",
                         "_links": {"webui": "/spaces/TechOps/pages/42/T"}}
        raise AssertionError(f"unexpected {method} {url}")

    res = publish_scorecard(_make_report(), "<p>x</p>", "T", _cfg(), http_fn=http_fn)
    assert res["published"] is True
    assert res["action"] == "updated"


# ---------- auth ----------

def test_publish_sends_basic_auth_header():
    seen = {}

    def http_fn(method, url, headers, body, timeout):
        seen["auth"] = headers.get("Authorization", "")
        if method == "GET":
            return 200, {"results": []}
        return 200, {"id": "1", "_links": {"webui": "/x"}}

    publish_scorecard(_make_report(), "<p>x</p>", "T", _cfg(), http_fn=http_fn)
    assert seen["auth"].startswith("Basic ")
    decoded = base64.b64decode(seen["auth"].split(" ", 1)[1]).decode()
    assert decoded == "tech@siae.it:TOKEN123"


# ---------- fail-open ----------

def test_publish_fail_open_on_http_error():
    def http_fn(method, url, headers, body, timeout):
        raise RuntimeError("network down")

    res = publish_scorecard(_make_report(), "<p>x</p>", "T", _cfg(), http_fn=http_fn)
    assert res["published"] is False
    assert res["action"] == "error"
    assert "reason" in res  # nessuna eccezione propagata


def test_publish_fail_open_on_non_2xx():
    def http_fn(method, url, headers, body, timeout):
        if method == "GET":
            return 200, {"results": []}
        return 403, {"message": "forbidden"}

    res = publish_scorecard(_make_report(), "<p>x</p>", "T", _cfg(), http_fn=http_fn)
    assert res["published"] is False
    assert res["action"] == "error"
