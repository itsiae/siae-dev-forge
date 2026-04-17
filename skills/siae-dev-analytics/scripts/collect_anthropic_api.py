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
            msg = f"Anthropic API timeout (attempt {attempt+1}/{MAX_RETRIES}). Verifica connettivita."
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
