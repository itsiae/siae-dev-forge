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


# --- Task 03: retrocompat snapshot legacy ---

def test_legacy_snapshot_no_crash():
    legacy = {"input": 100, "output": 50, "cache_read": 10,
              "cache_write": 200, "cost_eur": 0.123, "model": "claude-sonnet-4-6"}
    normalized = tc.normalize_usage_snapshot(legacy)
    assert normalized["cost_eur"] == 0.123
    assert normalized["cache_write_5m"] == 0
    assert normalized["cache_write_1h"] == 0


def test_legacy_stats_normalize_no_crash():
    legacy_stats = {"input": 100, "output": 50, "cache_read": 10,
                    "cache_write": 200, "cost_eur": 0.5}
    stats = tc.normalize_stats(legacy_stats)
    assert stats["cost_eur"] == 0.5
    assert stats["cache_write"] == 0


# --- Task 04: dedup tool delega al core ---

def _load_tool():
    tool_path = REPO_ROOT / "tests" / "analyze-token-usage.py"
    spec = importlib.util.spec_from_file_location("analyze_token_usage", tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_delegates_to_core():
    tool = _load_tool()
    usage = {"input_tokens": 1000, "output_tokens": 500,
             "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 300}
    event = {"type": "assistant", "message": {"model": "claude-sonnet-4-6", "usage": usage}}
    tool_cost = tool.cost_for_usage(event, usage)
    core_cost = tc.usage_cost_eur(tc.usage_tokens(usage), "claude-sonnet-4-6")
    assert abs(tool_cost - core_cost) < 1e-9


def test_tool_has_no_local_pricing():
    tool_src = (REPO_ROOT / "tests" / "analyze-token-usage.py").read_text()
    assert "PRICING = {" not in tool_src
    assert "def calculate_cost" not in tool_src


# --- Task 05: modello prevalente + token in telemetria ---

def _snapshot(model, total):
    return {"input": total, "output": 0, "cache_read": 0, "cache_write_5m": 0,
            "cache_write_1h": 0, "cache_write": 0, "total": total,
            "model": model, "cost_eur": 0.0}


def test_model_prevalent_picks_max_tokens():
    stats = tc.empty_stats()
    tc.add_usage_delta(stats, None, _snapshot("claude-sonnet-4-6", 1000))
    tc.add_usage_delta(stats, None, _snapshot("claude-opus-4-6", 5000))
    tc.finalize_model_prevalent(stats)
    assert stats["model_prevalent"] == "claude-opus-4-6"
    assert stats["by_model"]["claude-sonnet-4-6"] == 1000
    assert stats["by_model"]["claude-opus-4-6"] == 5000


def test_model_prevalent_tiebreak_alphabetical():
    stats = tc.empty_stats()
    tc.add_usage_delta(stats, None, _snapshot("claude-sonnet-4-6", 1000))
    tc.add_usage_delta(stats, None, _snapshot("claude-opus-4-6", 1000))
    tc.finalize_model_prevalent(stats)
    # parità → ordine alfabetico → "claude-opus-4-6" < "claude-sonnet-4-6"
    assert stats["model_prevalent"] == "claude-opus-4-6"


def test_normalize_stats_without_by_model_no_crash():
    legacy = {"input": 100, "output": 50, "cache_read": 0, "cache_write_5m": 0,
              "cache_write_1h": 0, "cost_eur": 0.1}
    stats = tc.normalize_stats(legacy)
    assert stats["by_model"] == {}
    assert stats["model_prevalent"] == ""
