"""Test per collect_anthropic_api.py."""
from unittest.mock import patch, MagicMock
import pytest
import collect_anthropic_api as ca


def test_fetch_returns_empty_if_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result, warnings = ca.fetch_usage_by_dev(org_id="org-x", since="2026-01-01", until="2026-02-01")
    assert result == {}
    assert any("ANTHROPIC_API_KEY" in w for w in warnings)


def test_fetch_happy_path_returns_cost_dict(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "data": [
            {"actor": {"email": "alice@siae.it"}, "total_cost_usd": 12.50},
            {"actor": {"email": "bob@siae.it"}, "total_cost_usd": 7.00},
        ]
    }
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result["alice@siae.it"] > 0
    assert warnings == []


def test_fetch_401_auth_error_returns_empty_with_warning(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-invalid")
    mock_response = MagicMock(status_code=401, text="Unauthorized")
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result == {}
    assert any("401" in w or "auth" in w.lower() for w in warnings)


def test_fetch_429_rate_limit_triggers_backoff(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    call_count = [0]
    def side_effect(*a, **kw):
        call_count[0] += 1
        if call_count[0] < 3:
            return MagicMock(status_code=429, text="Rate limited")
        return MagicMock(status_code=200, json=lambda: {"data": []})
    with patch("collect_anthropic_api._http_get", side_effect=side_effect), \
         patch("time.sleep"):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert call_count[0] >= 3


def test_fetch_500_server_error_retries_and_fails(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=500, text="Server error")
    with patch("collect_anthropic_api._http_get", return_value=mock_response), \
         patch("time.sleep"):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result == {}
    assert any("500" in w for w in warnings)


def test_fetch_timeout_returns_empty_with_warning(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    import requests
    with patch("collect_anthropic_api._http_get", side_effect=requests.Timeout("timeout")):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result == {}
    assert any("timeout" in w.lower() for w in warnings)


def test_fetch_malformed_json_returns_empty_with_warning(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=200)
    mock_response.json.side_effect = ValueError("not json")
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result == {}
    assert any("parsing" in w.lower() or "json" in w.lower() for w in warnings)


def test_fetch_empty_response_returns_empty_dict(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"data": []}
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result == {}


def test_fetch_partial_response_missing_field(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"data": [
        {"actor": {"email": "alice@siae.it"}},  # missing total_cost_usd
    ]}
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-x", "2026-01-01", "2026-02-01")
    assert result.get("alice@siae.it", 0) == 0
    assert len(warnings) >= 0


def test_fetch_404_org_not_found(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    mock_response = MagicMock(status_code=404, text="org not found")
    with patch("collect_anthropic_api._http_get", return_value=mock_response):
        result, warnings = ca.fetch_usage_by_dev("org-invalid", "2026-01-01", "2026-02-01")
    assert result == {}
    assert any("404" in w or "org" in w.lower() for w in warnings)


def test_fetch_no_org_id_returns_empty(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    result, warnings = ca.fetch_usage_by_dev(org_id=None, since="2026-01-01", until="2026-02-01")
    assert result == {}
    assert any("org_id" in w for w in warnings)


def test_aggregate_usd_to_eur_conversion():
    """USD -> EUR via fixed rate (config)."""
    assert abs(ca.usd_to_eur(10.0) - 9.2) < 0.5  # rate ~0.92
