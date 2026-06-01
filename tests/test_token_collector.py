"""Test per lib/token-collector.py — accuratezza calcolo costi token.

Import del modulo con trattino nel filename via importlib (pattern test_anti_bloat_lint.py).
"""
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "lib" / "token-collector.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("token_collector", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tc = _load_module()


def _metrics(**kw):
    base = {
        "input": 0, "output": 0, "cache_read": 0,
        "cache_write_5m": 0, "cache_write_1h": 0, "cache_write": 0,
    }
    base.update(kw)
    base.setdefault("total", base["input"] + base["output"] + base["cache_read"]
                    + base["cache_write_5m"] + base["cache_write_1h"])
    return base


# --- Task 01: pricing differenziato cache 5m/1h ---

def test_cache_write_1h_priced_2x_input():
    cost_eur = tc.usage_cost_eur(_metrics(cache_write_1h=1_000_000, cache_write=1_000_000),
                                 "claude-sonnet-4-6")
    # 1M * 6.0 / 1M = 6.0 USD * 0.91 = 5.46 EUR
    assert abs(cost_eur - 5.46) < 0.01


def test_cache_write_5m_priced_1_25x_input():
    cost_eur = tc.usage_cost_eur(_metrics(cache_write_5m=1_000_000, cache_write=1_000_000),
                                 "claude-sonnet-4-6")
    # 1M * 3.75 / 1M = 3.75 USD * 0.91 = 3.4125 EUR
    assert abs(cost_eur - 3.4125) < 0.01


def test_mix_5m_1h_sums_both_rates():
    cost_eur = tc.usage_cost_eur(
        _metrics(cache_write_5m=1_000_000, cache_write_1h=1_000_000, cache_write=2_000_000),
        "claude-sonnet-4-6")
    # (3.75 + 6.0) USD * 0.91 = 8.8725 EUR
    assert abs(cost_eur - 8.8725) < 0.01


def test_unknown_model_falls_back_to_default():
    cost_eur = tc.usage_cost_eur(_metrics(input=1_000_000), "gpt-nonexistent")
    # default input 3.0 USD * 0.91 = 2.73 EUR
    assert abs(cost_eur - 2.73) < 0.01


# --- Task 02: tasso EUR via env var ---

def test_eur_rate_override(monkeypatch):
    monkeypatch.setenv("DEVFORGE_USD_EUR_RATE", "1.0")
    assert tc.resolve_eur_rate() == 1.0


def test_eur_rate_default(monkeypatch):
    monkeypatch.delenv("DEVFORGE_USD_EUR_RATE", raising=False)
    assert tc.resolve_eur_rate() == 0.91


def test_eur_rate_malformed_falls_back(monkeypatch):
    monkeypatch.setenv("DEVFORGE_USD_EUR_RATE", "not-a-number")
    assert tc.resolve_eur_rate() == 0.91


def test_eur_rate_one_means_cost_eur_equals_usd(monkeypatch):
    monkeypatch.setenv("DEVFORGE_USD_EUR_RATE", "1.0")
    cost = tc.usage_cost_eur(_metrics(input=1_000_000), "claude-sonnet-4-6")
    assert abs(cost - 3.0) < 0.01  # 3.0 USD, rate 1.0 → 3.0
