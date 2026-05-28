"""Validate vitest-jest-compat.json structure.

The asset was drafted during the 3-blind-agent synthesis phase. This test
verifies it conforms to the contract expected by detect_jest_incompat.py
and migrate_jest_to_vitest.py.
"""
import json
from pathlib import Path


ASSET = (
    Path(__file__).resolve().parent.parent.parent
    / "assets"
    / "vitest-jest-compat.json"
)


def test_asset_is_valid_json():
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    assert "version" in data
    assert "incompatibility_signals" in data
    assert "non_incompatibilities" in data
    assert "migration_targets" in data
    assert "api_migration_map" in data


def test_all_10_signals_present():
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    signals = data["incompatibility_signals"]
    expected = {f"I{i}" for i in range(1, 11)}
    assert set(signals.keys()) == expected


def test_signals_have_required_fields():
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    for sig_id, sig in data["incompatibility_signals"].items():
        assert "name" in sig, f"{sig_id} missing 'name'"
        assert "description" in sig, f"{sig_id} missing 'description'"
        assert "detect" in sig, f"{sig_id} missing 'detect'"
        assert "fix_hint" in sig, f"{sig_id} missing 'fix_hint'"
        assert "kind" in sig["detect"], f"{sig_id}.detect missing 'kind'"


def test_i5_allowlist_excludes_preset():
    """WARN-3 fix: @babel/preset-typescript is a preset, not a transformer."""
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    allowlist = data["incompatibility_signals"]["I5"]["detect"]["allowlist"]
    assert "@babel/preset-typescript" not in allowlist
    assert "ts-jest" in allowlist
    assert "babel-jest" in allowlist


def test_setupFilesAfterEach_not_silently_remapped():
    """WARN-2 fix: setupFilesAfterEach has no Vitest equivalent."""
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    cmap = data["api_migration_map"]["config_key_map"]
    assert cmap["setupFilesAfterEach"] == "MANUAL_REVIEW_NOT_EQUIVALENT"


def test_no_rewrite_tokens_listed():
    """Amendment-4: requireActual/requireMock are flagged only, not rewritten."""
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    no_rewrite = data["api_migration_map"]["no_rewrite_tokens"]
    assert "jest.requireActual" in no_rewrite
    assert "jest.requireMock" in no_rewrite


def test_config_keys_manual_review_listed():
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    crm = data["api_migration_map"]["config_keys_manual_review"]
    assert "setupFilesAfterEach" in crm
    assert "globalSetup" in crm
    assert "globalTeardown" in crm


def test_api_migration_map_has_at_least_21_rewrites():
    data = json.loads(ASSET.read_text(encoding="utf-8"))
    rewrites = data["api_migration_map"]["rewrites"]
    assert len(rewrites) >= 21
