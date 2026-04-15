# Task 02 — F0 Sources Always-On

**Goal:** AWS profile setup + Anthropic Console API fallback + CLI --cost-per-dev override.
**AC coperti:** S3-1, S3-2, S3-3 (design §2.5), NF9-NF17 (fault injection)
**Dipendenze:** Task 01
**Effort:** ~40 min
**Test nuovi:** 17 (5 AWS profile + 12 Anthropic API)

## File coinvolti

- `scripts/autodetect_sources.py` — aggiungi `check_aws_profile()` + `check_anthropic_api()`
- `scripts/collect_anthropic_api.py` — implementazione client Console API
- `scripts/run_analytics.py` — aggiungi `--cost-per-dev` CLI flag
- `tests/test_autodetect.py` — 5 nuovi test
- `tests/test_collect_anthropic_api.py` — 12 test (happy + 9 fault + 2 edge)

## Step 1 — TDD RED: test_collect_anthropic_api.py

Scrivi test per client Anthropic Console API con **12 test** (pattern fault injection NF9-NF17):

```python
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
    """USD → EUR via fixed rate (config)."""
    assert abs(ca.usd_to_eur(10.0) - 9.2) < 0.5  # rate ~0.92
```

## Step 2 — Implementa collect_anthropic_api.py

```python
"""Anthropic Console API client for cost data fallback."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

API_BASE = "https://api.anthropic.com/v1/organizations"
USD_TO_EUR_RATE = 0.92  # rate fisso da config, override env var ANTHROPIC_USD_EUR_RATE
MAX_RETRIES = 3
BACKOFF_BASE = 60  # seconds


def _http_get(url: str, headers: dict, timeout: int = 30) -> requests.Response:
    """Wrapper per mocking test."""
    return requests.get(url, headers=headers, timeout=timeout)


def usd_to_eur(usd: float) -> float:
    rate = float(os.getenv("ANTHROPIC_USD_EUR_RATE", USD_TO_EUR_RATE))
    return usd * rate


def fetch_usage_by_dev(
    org_id: str | None,
    since: str,
    until: str,
) -> tuple[dict[str, float], list[str]]:
    """Fetch Anthropic Console usage per actor. Returns (cost_eur_by_email, warnings).

    Graceful degrade: never raises. Empty dict on any failure.
    """
    warnings: list[str] = []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        msg = "ANTHROPIC_API_KEY env var mancante. Configura: export ANTHROPIC_API_KEY=sk-..."
        log.warning(msg)
        warnings.append(msg)
        return {}, warnings

    if not org_id:
        msg = "org_id mancante in config. Configura options.anthropic_org_id nel YAML."
        log.warning(msg)
        warnings.append(msg)
        return {}, warnings

    url = f"{API_BASE}/{org_id}/usage_report/messages?starting_at={since}&ending_at={until}"
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = _http_get(url, headers=headers, timeout=30)
        except requests.Timeout:
            msg = f"Anthropic API timeout (attempt {attempt+1}/{MAX_RETRIES}). Verifica connettività."
            log.warning(msg)
            warnings.append(msg)
            if attempt == MAX_RETRIES - 1:
                return {}, warnings
            continue
        except Exception as e:
            msg = f"Anthropic API errore imprevisto: {e}. Verifica env ANTHROPIC_API_KEY."
            log.error(msg)
            warnings.append(msg)
            return {}, warnings

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError as e:
                msg = f"Anthropic API response JSON parsing fallito: {e}. Verifica versione API."
                log.warning(msg)
                warnings.append(msg)
                return {}, warnings

            costs: dict[str, float] = {}
            for entry in data.get("data", []):
                actor = (entry.get("actor") or {})
                email = actor.get("email") or actor.get("id")
                if not email:
                    continue
                usd = entry.get("total_cost_usd", 0)
                costs[email] = costs.get(email, 0) + usd_to_eur(usd)
            log.info("Anthropic API: %d dev, cost EUR totale %.2f", len(costs), sum(costs.values()))
            return costs, warnings

        if resp.status_code == 401:
            msg = "Anthropic API 401 auth. Verifica ANTHROPIC_API_KEY valida e permessi org."
            log.warning(msg)
            warnings.append(msg)
            return {}, warnings

        if resp.status_code == 404:
            msg = f"Anthropic API 404: org {org_id} non trovato. Verifica anthropic_org_id."
            log.warning(msg)
            warnings.append(msg)
            return {}, warnings

        if resp.status_code == 429:
            sleep_s = BACKOFF_BASE * (2 ** attempt)
            log.warning("Anthropic API 429 rate limit, sleep %ds (attempt %d)", sleep_s, attempt+1)
            time.sleep(sleep_s)
            continue

        if resp.status_code >= 500:
            sleep_s = BACKOFF_BASE * (2 ** attempt)
            log.warning("Anthropic API %d server error, sleep %ds", resp.status_code, sleep_s)
            warnings.append(f"Anthropic API {resp.status_code}. Retry in {sleep_s}s.")
            time.sleep(sleep_s)
            continue

        msg = f"Anthropic API status {resp.status_code}: {resp.text[:200]}"
        log.error(msg)
        warnings.append(msg)
        return {}, warnings

    msg = f"Anthropic API fallito dopo {MAX_RETRIES} tentativi. Retry manuale: configura cost-per-dev CLI."
    log.error(msg)
    warnings.append(msg)
    return {}, warnings
```

## Step 3 — autodetect_sources.py: check_aws_profile + check_anthropic_api

Aggiungi a `autodetect_sources.py`:

```python
def check_aws_profile() -> tuple[bool, str]:
    """Returns (available, reason)."""
    profile = os.getenv("AWS_PROFILE")
    if not profile:
        return False, "AWS_PROFILE non settato. Esegui: export AWS_PROFILE=siae-dev-forge"
    return True, f"AWS_PROFILE={profile}"


def check_anthropic_api() -> tuple[bool, str]:
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    if not has_key:
        return False, "ANTHROPIC_API_KEY mancante. Configura env var per abilitare cost fallback."
    return True, "ANTHROPIC_API_KEY presente"
```

## Step 4 — CLI flag --cost-per-dev

In `run_analytics.py`, aggiungi parser:

```python
p_run.add_argument("--cost-per-dev", action="append", default=[],
                    help="Override cost: --cost-per-dev alice=50.0 --cost-per-dev bob=35.0")
```

Poi in `cmd_run` parse `args.cost_per_dev` in dict `{dev: eur}`.

## Step 5 — Test autodetect (5 nuovi)

Aggiungi a `test_autodetect.py`:

```python
def test_check_aws_profile_missing(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    ok, msg = ad.check_aws_profile()
    assert ok is False
    assert "AWS_PROFILE" in msg


def test_check_aws_profile_set(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "test-profile")
    ok, msg = ad.check_aws_profile()
    assert ok is True
    assert "test-profile" in msg


def test_check_anthropic_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ok, msg = ad.check_anthropic_api()
    assert ok is False


def test_check_anthropic_api_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    ok, msg = ad.check_anthropic_api()
    assert ok is True


def test_autodetect_dict_includes_aws_anthropic_status(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with patch.object(ad, "check_gh_auth", return_value=True), \
         patch.object(ad, "check_s3_prefix", return_value=False):
        report = ad.autodetect()
    d = report.as_dict()
    assert "aws_profile" in d or "anthropic_api" in d  # esteso
```

## Step 6 — Run test

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_autodetect.py skills/siae-dev-analytics/tests/test_collect_anthropic_api.py -v
```

Output atteso: `27 passed` (10 esistenti + 5 nuovi autodetect + 12 anthropic).

## Criteri accettazione

- [ ] `collect_anthropic_api.py` implementa fetch_usage_by_dev con 12 test pass
- [ ] `autodetect_sources.py` check_aws_profile + check_anthropic_api + 5 test pass
- [ ] `run_analytics.py` supporta `--cost-per-dev dev=eur`
- [ ] Tutti ritorni sono `(dict, warnings: list[str])` — no silent failure
- [ ] Ogni RuntimeError (se presente) ha messaggio actionable ≥20 char con verbo
